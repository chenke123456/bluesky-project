from __future__ import annotations

from copy import deepcopy
from typing import Any

from comfy_api.latest import io

from .blue_core import (
    BLUE_ENTITY_PACK,
    BLUE_RULE_PACK,
    BLUE_WORLD,
    collect_entities,
    collect_rules,
    stable_id,
)


# World intentionally owns no entity geometry defaults.
# Entity geometry is defined by Entity/Rules and visual fallback by Renderer.
TYPE_COLOR = {
    "house": "#8b949e",
    "room": "#6e7681",
    "human": "#58a6ff",
    "machine": "#d29922",
    "device": "#3fb950",
    "furniture": "#a371f7",
    "door": "#f0883e",
    "wall": "#484f58",
    "plant": "#2ea043",
    "animal": "#db61a2",
    "custom": "#8b949e",
}


def _entity_type(entity: dict[str, Any]) -> str:
    return str(entity.get("entity_type") or entity.get("type") or entity.get("name") or "custom")


def _rule_option(entity: dict[str, Any], rule_name: str) -> str | None:
    rules = entity.get("rules")
    if not isinstance(rules, list):
        return None

    # Rules use last-writer-wins semantics throughout BlueNode.  Scan backwards
    # here too, so World never revives an older value if it receives legacy data
    # that still contains duplicate rules.
    expected_type = {
        "颜色规则": "color",
    }.get(rule_name)

    for rule in reversed(rules):
        if not isinstance(rule, dict):
            continue
        if rule.get("name") != rule_name and (not expected_type or rule.get("rule_type") != expected_type):
            continue
        # 颜色规则由 BlueRuleNode 使用唯一的 Python COLOR_MAP 编译成 HEX。
        # World 直接写入该 canonical value，避免把“浅蓝/海军蓝”等标签传给渲染器。
        if rule_name == "颜色规则":
            params = rule.get("params")
            if isinstance(params, dict) and params.get("color"):
                return str(params["color"])
        options = rule.get("options")
        if isinstance(options, list) and options:
            return str(options[0])
    return None


def _compile_entity_state(entity: dict[str, Any], index: int) -> dict[str, Any]:
    item = deepcopy(entity)
    etype = _entity_type(item)
    item.setdefault("entity_type", etype)
    item.setdefault("id", stable_id("entity", [index, item]))

    # Existing explicit backend transform remains a compatibility/fallback path.
    # Position rules themselves are not converted here: 3D position vectors are
    # interpreted by the Three.js selector, and 2D vectors by the UI runtime.
    if not isinstance(item.get("transform"), dict):
        x = float((index % 5) * 2 - 4)
        y = 0.0
        z = float((index // 5) * 2)
        item["transform"] = {
            "position": {"x": x, "y": y, "z": z},
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
        }

    if not isinstance(item.get("motion"), dict):
        item["motion"] = {"velocity": {"x": 0.0, "y": 0.0, "z": 0.0}}

    if not isinstance(item.get("interaction"), dict):
        item["interaction"] = {
            "selectable": True,
            "action_enabled": etype in {"door", "device", "machine", "human"},
        }

    # 颜色规则属于“实体状态规则”，在后端直接落成 appearance.color。
    # 规则是用户显式选择，因此优先于实体默认色；切换下拉值后重新运行即可得到新的 HEX。
    appearance = item.get("appearance")
    if not isinstance(appearance, dict):
        appearance = {}
        item["appearance"] = appearance

    existing_color = appearance.get("color")
    color_rule = _rule_option(item, "颜色规则")
    if color_rule:
        # Highest-priority source: a rule attached to the effective entity.
        # Instance rules have already replaced template rules before this point.
        appearance["color"] = color_rule
        appearance["color_source"] = "rule"
    elif existing_color:
        # Preserve an explicitly supplied backend appearance color.
        appearance.setdefault("color_source", "explicit")
    else:
        appearance["color"] = TYPE_COLOR.get(etype, TYPE_COLOR["custom"])
        appearance["color_source"] = "default"

    # World 不编译三维几何。有效规则原样进入前端，由 Three.js Selector 解释。
    item.pop("render_spec", None)

    return item


class BlueWorldNode(io.ComfyNode):
    """Compile a static world definition. It does not create or run a simulation."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueWorldNode",
            display_name="世界",
            category="Blue/Simulation",
            inputs=[
                BLUE_ENTITY_PACK.Input("entities", optional=True),
                BLUE_RULE_PACK.Input("rules", optional=True),
                io.String.Input("world_name", default="city"),
            ],
            outputs=[BLUE_WORLD.Output(display_name="JSON")],
        )

    @classmethod
    def execute(cls, entities=None, rules=None, world_name="city") -> io.NodeOutput:
        source_entities = collect_entities(entities)
        compiled_entities = [
            _compile_entity_state(entity, index)
            for index, entity in enumerate(source_entities)
            if isinstance(entity, dict)
        ]

        world = {
            "kind": "BLUE_WORLD",
            "name": str(world_name or "city"),
            "tick": 0,
            "time": 0.0,
            "entities": compiled_entities,
            "rules": collect_rules(rules),
        }
        return io.NodeOutput(world)
