from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from comfy_api.latest import io

from .blue_core import (
    BLUE_ENTITY,
    BLUE_ENTITY_PACK,
    BLUE_RULE_PACK,
    collect_rules,
    maybe_json,
    stable_id,
)


PATTERN_OPTIONS = ["线性", "网格", "圆周", "重叠"]


def _format_name(pattern: str, template: dict[str, Any], index: int) -> str:
    base_name = str(
        template.get("entity_name")
        or template.get("name")
        or template.get("entity_item")
        or "Entity"
    )
    replacements = {
        "{name}": base_name,
        "{index}": str(index),
        "{index1}": str(index + 1),
    }
    result = str(pattern or "{name}_{index}")
    for token, value in replacements.items():
        result = result.replace(token, value)
    return result


def _position_for(
    pattern: str,
    index: int,
    count: int,
    *,
    origin_x: float,
    origin_y: float,
    origin_z: float,
    spacing_x: float,
    spacing_y: float,
    spacing_z: float,
    columns: int,
    radius: float,
    start_angle_deg: float,
    total_angle_deg: float,
) -> dict[str, float]:
    if pattern == "网格":
        columns = max(1, int(columns))
        column = index % columns
        row = index // columns
        return {
            "x": origin_x + column * spacing_x,
            "y": origin_y + row * spacing_y,
            "z": origin_z + row * spacing_z,
        }

    if pattern == "圆周":
        radius = max(0.0, float(radius))
        start = math.radians(float(start_angle_deg))
        span_deg = float(total_angle_deg)
        span = math.radians(span_deg)
        closed = abs(abs(span_deg) - 360.0) < 1e-6
        denominator = max(1, count if closed else count - 1)
        angle = start + span * (index / denominator)
        return {
            "x": origin_x + math.cos(angle) * radius,
            "y": origin_y,
            "z": origin_z + math.sin(angle) * radius,
        }

    if pattern == "重叠":
        return {"x": origin_x, "y": origin_y, "z": origin_z}

    return {
        "x": origin_x + index * spacing_x,
        "y": origin_y + index * spacing_y,
        "z": origin_z + index * spacing_z,
    }


def _rule_key(rule: dict[str, Any]) -> tuple[str, str]:
    return (
        str(rule.get("rule_kind") or "property"),
        str(rule.get("rule_type") or rule.get("name") or "custom"),
    )


def _substitute_instance_tokens(value: Any, index: int, count: int, name: str) -> Any:
    """Replace lightweight instance tokens inside rule strings.

    This keeps instance differences inside the rule system without creating a separate
    parameter node. Standard rules work unchanged; custom rules may use {index},
    {index1}, {count}, and {name} in string values.
    """
    if isinstance(value, str):
        return (
            value.replace("{index}", str(index))
            .replace("{index1}", str(index + 1))
            .replace("{count}", str(count))
            .replace("{name}", name)
        )
    if isinstance(value, list):
        return [_substitute_instance_tokens(v, index, count, name) for v in value]
    if isinstance(value, dict):
        return {
            str(k): _substitute_instance_tokens(v, index, count, name)
            for k, v in value.items()
        }
    return deepcopy(value)


def _merge_rules(
    template_rules: list[dict[str, Any]],
    instance_rules: list[dict[str, Any]],
    index: int,
    count: int,
    name: str,
) -> list[dict[str, Any]]:
    """Merge rules with strict last-writer-wins semantics.

    Rules connected to the Entity Instancer are applied *after* rules already
    attached to the entity template.  For the same ``rule_kind + rule_type``
    only the last rule is kept, so an instance rule always overrides every
    earlier/template rule of that type.  This also removes duplicate template
    rules that could otherwise make downstream consumers pick an older value.
    """
    candidates: list[dict[str, Any]] = []

    # Template/entity rules are the lower-priority layer.
    for raw_rule in template_rules:
        if isinstance(raw_rule, dict):
            candidates.append(deepcopy(raw_rule))

    # Instancer input rules are the higher-priority layer.  Token substitution
    # happens before de-duplication so custom per-instance values are retained.
    for raw_rule in instance_rules:
        if isinstance(raw_rule, dict):
            candidates.append(_substitute_instance_tokens(raw_rule, index, count, name))

    # Traverse backwards: the first key we see is the effective rule.  Reverse
    # again at the end to keep deterministic source order for unrelated rules.
    seen: set[tuple[str, str]] = set()
    effective_reversed: list[dict[str, Any]] = []
    for rule in reversed(candidates):
        key = _rule_key(rule)
        if key in seen:
            continue
        seen.add(key)
        effective_reversed.append(rule)

    return list(reversed(effective_reversed))


def materialize_instance_pack(pack: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand a compact BLUE_ENTITY_INSTANCE_PACK into normal Blue entities."""
    if not isinstance(pack, dict) or pack.get("kind") != "BLUE_ENTITY_INSTANCE_PACK":
        return []

    template = pack.get("template")
    records = pack.get("instances")
    # instance_rules is stored as a list in the compact pack. collect_rules now
    # accepts lists directly; keeping this explicit call documents that these are
    # the highest-priority rules during materialization.
    instance_rules = collect_rules(pack.get("instance_rules"))
    if not isinstance(template, dict) or not isinstance(records, list):
        return []

    template_rules = collect_rules(template.get("rules"))
    result: list[dict[str, Any]] = []
    count = len(records)

    for record in records:
        if not isinstance(record, dict):
            continue
        index = int(record.get("index", len(result)))
        name = str(record.get("name") or template.get("entity_name") or template.get("name") or "Entity")
        entity = deepcopy(template)
        rules = _merge_rules(template_rules, instance_rules, index, count, name)

        entity["id"] = str(record.get("id") or stable_id("instance", record))
        entity["name"] = name
        entity["entity_name"] = name
        entity["instance_of"] = pack.get("template_id")
        entity["instance_index"] = index
        entity["transform"] = deepcopy(record.get("transform") or {})
        entity["rules"] = rules
        entity["properties"] = [rule for rule in rules if rule.get("rule_kind") != "method"]
        entity["methods"] = [rule for rule in rules if rule.get("rule_kind") == "method"]

        # Materialized instances expose their effective color immediately.
        # This makes the instancer override authoritative even for downstream
        # consumers that render entities without first passing through World.
        for effective_rule in reversed(rules):
            if not isinstance(effective_rule, dict):
                continue
            if effective_rule.get("rule_type") != "color" and effective_rule.get("name") != "颜色规则":
                continue
            params = effective_rule.get("params")
            if isinstance(params, dict) and params.get("color"):
                appearance = entity.get("appearance")
                if not isinstance(appearance, dict):
                    appearance = {}
                    entity["appearance"] = appearance
                appearance["color"] = str(params["color"])
                appearance["color_source"] = "instance_rule"
                break

        # 实例化器只合并/传递规则，不生成 Three.js 几何描述。
        entity.pop("render_spec", None)

        result.append(entity)

    return result


class BlueEntityInstancerNode(io.ComfyNode):
    """Create many entity instances from one entity template and optional rule overrides."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueEntityInstancerNode",
            display_name="实体实例器",
            category="Blue/Entities",
            inputs=[
                BLUE_ENTITY.Input("实体模板"),
                BLUE_RULE_PACK.Input("实例规则", optional=True),
                io.Int.Input("数量", default=10, min=1, max=10000, step=1),
                io.Combo.Input("排列模式", options=PATTERN_OPTIONS),
                io.String.Input("命名规则", default="{name}_{index}", multiline=False),
                io.Float.Input("起点X", default=0.0, step=0.1),
                io.Float.Input("起点Y", default=0.0, step=0.1),
                io.Float.Input("起点Z", default=0.0, step=0.1),
                io.Float.Input("间距X", default=2.0, step=0.1),
                io.Float.Input("间距Y", default=0.0, step=0.1),
                io.Float.Input("间距Z", default=0.0, step=0.1),
                io.Int.Input("每行数量", default=10, min=1, max=10000, step=1),
                io.Float.Input("圆周半径", default=10.0, min=0.0, step=0.1),
                io.Float.Input("起始角度", default=0.0, step=1.0),
                io.Float.Input("总角度", default=360.0, step=1.0),
            ],
            outputs=[BLUE_ENTITY_PACK.Output(display_name="实体实例")],
        )

    @classmethod
    def execute(
        cls,
        实体模板,
        数量=10,
        排列模式="线性",
        命名规则="{name}_{index}",
        起点X=0.0,
        起点Y=0.0,
        起点Z=0.0,
        间距X=2.0,
        间距Y=0.0,
        间距Z=0.0,
        每行数量=10,
        圆周半径=10.0,
        起始角度=0.0,
        总角度=360.0,
        实例规则=None,
    ) -> io.NodeOutput:
        template = maybe_json(实体模板, 实体模板)
        if not isinstance(template, dict):
            return io.NodeOutput({"kind": "BLUE_ENTITY_INSTANCE_PACK", "template": {}, "instances": []})

        count = max(1, min(10000, int(数量)))
        template_id = str(template.get("template_id") or template.get("id") or stable_id("template", template))
        instance_rules = collect_rules(实例规则)

        records: list[dict[str, Any]] = []
        for index in range(count):
            name = _format_name(str(命名规则 or "{name}_{index}"), template, index)
            position = _position_for(
                str(排列模式 or "线性"),
                index,
                count,
                origin_x=float(起点X),
                origin_y=float(起点Y),
                origin_z=float(起点Z),
                spacing_x=float(间距X),
                spacing_y=float(间距Y),
                spacing_z=float(间距Z),
                columns=max(1, int(每行数量)),
                radius=max(0.0, float(圆周半径)),
                start_angle_deg=float(起始角度),
                total_angle_deg=float(总角度),
            )
            transform = {
                "position": position,
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
            }
            records.append({
                "id": stable_id("instance", [template_id, index, name, transform]),
                "index": index,
                "name": name,
                "transform": transform,
            })

        pack = {
            "kind": "BLUE_ENTITY_INSTANCE_PACK",
            "template_id": template_id,
            "template": deepcopy(template),
            "count": count,
            "instance_rules": deepcopy(instance_rules),
            "instances": records,
        }
        return io.NodeOutput(pack)
