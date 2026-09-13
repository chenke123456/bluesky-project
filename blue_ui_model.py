from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Dict, Iterable, List

from .blue_core import collect_entities, maybe_json


UI_SCHEMA = "bluenode.ui.v2"
DATA_SCHEMA = "bluenode.data.v1"

# 只有“网站”实体才参与 UI 投影。
# 设备、人物、家具、建筑、自然对象等都属于业务/世界数据，
# 它们可以进入 DATA_CONTEXT 被 React UI / Three.js 读取，但不会自动生成界面组件。
WEBSITE_VIEW_PROJECTION = {
    "页面": {"renderer": "react", "component": "react.Page"},
    "面板": {"renderer": "react", "component": "react.Panel"},
    "按钮": {"renderer": "react", "component": "react.Button"},
    "分隔线": {"renderer": "react", "component": "react.Divider"},
    "控件": {"renderer": "react", "component": "react.Control"},
    "卡片": {"renderer": "react", "component": "react.Card"},
    "人物信息": {"renderer": "react", "component": "react.Person"},
    "状态": {"renderer": "react", "component": "react.Status"},
    "指示器": {"renderer": "react", "component": "react.Indicator"},
    "装饰": {"renderer": "react", "component": "react.Decoration"},
    "3D视图": {"renderer": "three", "component": "three.Viewer"},
}


def _is_website_entity(entity: Dict[str, Any]) -> bool:
    return str(entity.get("entity_category") or "").strip() == "网站"


POSITION_REGION_MAP = {
    "左侧": "left",
    "右侧": "right",
    "上方": "top",
    "下方": "bottom",
    "中心": "center",
    "内部": "center",
    "外部": "overlay",
    "相邻": "center",
    "自定义位置": "auto",
}

RULE_TYPE_MAP = {
    "颜色规则": "appearance.color",
    "二维位置规则": "layout.position.2d",
    "三维位置规则": "world.position.3d",
    # 旧工作流兼容。
    "位置规则": "layout.position",
    "大小规则": "layout.size",
    "布局规则": "layout.controls",
    "绘制规则": "geometry.draw",
    "尺寸规则": "geometry.size",
    "镜头规则": "view.camera",
    "材料规则": "appearance.material",
    "强度规则": "analysis.strength",
    "刚度规则": "analysis.stiffness",
    "时间规则": "state.time",
    "传导规则": "behavior.conduction",
    "生长规则": "behavior.growth",
    "移动规则": "behavior.move",
    "点击规则": "behavior.click",
    "开关规则": "behavior.switch",
    "更新规则": "behavior.update",
    "作用域规则": "relation.scope",
    "拓扑规则": "layout.topology",
    "碰撞规则": "behavior.collision",
    "载荷规则": "layout.load",
    "稳定性规则": "state.stability",
    "自定义规则": "custom",
    "自定义属性规则": "custom.property",
    "自定义方法规则": "custom.method",
}


def _stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return f"{prefix}_{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:10]}"


def _extract_entities(payload: Any) -> List[Dict[str, Any]]:
    payload = maybe_json(payload, payload)
    if isinstance(payload, dict):
        entities = payload.get("entities")
        if isinstance(entities, list):
            return [item for item in entities if isinstance(item, dict)]
        if isinstance(payload.get("rules"), list) and payload.get("name"):
            return [payload]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def _extract_top_level_rules(payload: Any) -> List[Dict[str, Any]]:
    """Read rules from RulePack/World without attaching them to an entity.

    BlueNode's source model keeps Entity and Rule independent.  The UI runtime may
    interpret a top-level layout rule as a page-level website layout policy, but
    this function never mutates an entity or copies the rule into entity JSON.
    """
    payload = maybe_json(payload, payload)
    if not isinstance(payload, dict):
        return []

    candidates: List[Any] = []
    if isinstance(payload.get("rules"), list):
        candidates.extend(payload.get("rules") or [])
    else:
        if isinstance(payload.get("properties"), list):
            candidates.extend(payload.get("properties") or [])
        if isinstance(payload.get("methods"), list):
            candidates.extend(payload.get("methods") or [])

    return [rule for rule in candidates if isinstance(rule, dict)]


def _recursive_json_object_count(value: Any) -> int:
    if isinstance(value, dict):
        return 1 + sum(_recursive_json_object_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_recursive_json_object_count(v) for v in value)
    return 0


def _entity_type(entity: Dict[str, Any]) -> str:
    return str(entity.get("entity_type") or entity.get("type") or entity.get("name") or "custom")


def _entity_label(entity: Dict[str, Any], entity_type: str, index: int) -> str:
    explicit = entity.get("entity_name") or entity.get("label") or entity.get("title")
    if explicit and str(explicit) != entity_type:
        return str(explicit)
    return f"{entity_type} {index + 1}"


def _semantic_ui_label(entity_type: str, component: str, region: str, fallback: str) -> str:
    # 不修改现有 Entity 节点，也能让 UI 工作流得到可读的组件名称。
    if component == "react.Page":
        return "BlueNode Website"
    if component == "three.Viewer":
        return "3D Viewer"
    if component == "react.Button":
        return "重新计算"
    if component == "react.Status":
        return "状态"
    if component == "react.Card" and region == "bottom":
        return "实时数据"
    if component == "react.Panel":
        return {
            "top": "Header",
            "left": "Sidebar",
            "center": "Main Panel",
            "right": "Properties",
            "bottom": "Footer",
        }.get(region, fallback)
    return fallback


def _rules(entity: Dict[str, Any]) -> List[Dict[str, Any]]:
    rules = entity.get("rules", [])
    return [rule for rule in rules if isinstance(rule, dict)] if isinstance(rules, list) else []


def _compile_rule(rule: Dict[str, Any], target_id: str, index: int) -> Dict[str, Any]:
    name = str(rule.get("name") or rule.get("rule_name") or "自定义规则")
    options = rule.get("options")
    if not isinstance(options, list):
        option = rule.get("option")
        options = [] if option in (None, "") else [option]
    options = [str(item) for item in options if item not in (None, "")]
    params = rule.get("params") if isinstance(rule.get("params"), dict) else {}
    return {
        "id": _stable_id("uirule", [target_id, index, name, options, params]),
        "target": target_id,
        "name": name,
        "rule_kind": rule.get("rule_kind", "property"),
        "rule_type": RULE_TYPE_MAP.get(name, rule.get("rule_type", "custom")),
        "options": options,
        # Structured intermediate variables are preserved for React/Three/Simulation.
        "params": params,
        "source": rule,
    }


def _first_rule_option(compiled_rules: Iterable[Dict[str, Any]], rule_type: str) -> str | None:
    for rule in compiled_rules:
        if rule.get("rule_type") == rule_type:
            options = rule.get("options") or []
            if options:
                return str(options[0])
    return None


def _region_from_rules(compiled_rules: Iterable[Dict[str, Any]]) -> str:
    option = _first_rule_option(compiled_rules, "layout.position")
    return POSITION_REGION_MAP.get(option, "auto") if option else "auto"


def _view_projection(entity: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
    """Resolve a UI projection for a website entity only.

    Explicit view/component still has priority, but callers must first enforce
    entity_category == "网站". Non-website entities never reach this function.
    """
    explicit_view = entity.get("view")
    if isinstance(explicit_view, dict):
        component = explicit_view.get("component")
        renderer = explicit_view.get("renderer")
        if component:
            return {
                "renderer": str(renderer or "react"),
                "component": str(component),
                "props": explicit_view.get("props") if isinstance(explicit_view.get("props"), dict) else {},
                "explicit": True,
            }

    explicit_component = entity.get("component")
    if explicit_component:
        return {
            "renderer": str(entity.get("renderer") or "react"),
            "component": str(explicit_component),
            "props": entity.get("props") if isinstance(entity.get("props"), dict) else {},
            "explicit": True,
        }

    item = str(entity.get("entity_item") or "").strip()
    default = WEBSITE_VIEW_PROJECTION.get(item, WEBSITE_VIEW_PROJECTION["卡片"])
    return {**default, "props": {}, "explicit": False}


def _role_for_component(component: str) -> str:
    if component == "react.Page":
        return "page"
    if component in {"react.Panel", "react.Card"}:
        return "container"
    if component == "react.Button":
        return "action"
    if component == "three.Viewer":
        return "viewer"
    if component == "react.Divider":
        return "separator"
    return "component"


def compile_ui_model(payload: Any) -> Dict[str, Any]:
    """Compile an existing Blue Entity Pack into framework-neutral UI IR.

    Only website entities are compiled into UI IR. The resulting model separates:
      entity   -> what exists
      relation -> how entities are structured
      rule     -> constraints/behavior
      view     -> current renderer/component projection
    """
    raw = maybe_json(payload, payload)
    source_entities = _extract_entities(raw)
    source_global_rules = _extract_top_level_rules(raw)

    ui_entities: List[Dict[str, Any]] = []
    all_rules: List[Dict[str, Any]] = []
    root_id = None

    for index, entity in enumerate(source_entities):
        # 只有网站实体直接成为 UI。其他实体仍保留在 DATA_CONTEXT，
        # 可由网站组件绑定/读取，也可交给 Three.js 世界视图使用。
        if not _is_website_entity(entity):
            continue

        entity_type = _entity_type(entity)
        entity_id = str(entity.get("id") or _stable_id("uientity", [index, entity]))
        compiled_rules = [
            _compile_rule(rule, entity_id, rule_index)
            for rule_index, rule in enumerate(_rules(entity))
        ]
        all_rules.extend(compiled_rules)

        view = _view_projection(entity, entity_type)
        role = _role_for_component(view["component"])
        region = _region_from_rules(compiled_rules)
        fallback_label = _entity_label(entity, entity_type, index)
        label = _semantic_ui_label(entity_type, view["component"], region, fallback_label)
        if root_id is None and role == "page":
            root_id = entity_id

        ui_entities.append(
            {
                "id": entity_id,
                "entity_type": entity_type,
                "label": label,
                "role": role,
                "region": region,
                "view": view,
                "rules": [rule["id"] for rule in compiled_rules],
                "source_index": index,
                "source": entity,
            }
        )

    synthetic_root = False
    if root_id is None:
        root_id = "ui_root"
        synthetic_root = True

    # RulePack/World 顶层规则保持独立，不写入任何 Entity。网站运行时把其中
    # layout.controls 解释为页面级布局策略；其他全局规则可由各自执行器/渲染器读取。
    compiled_global_rules = [
        _compile_rule(rule, root_id, rule_index)
        for rule_index, rule in enumerate(source_global_rules)
    ]
    all_rules.extend(compiled_global_rules)

    # 现有节点没有显式 Relation target，因此 v2 只做“安全的默认包含关系”。
    # 作用域规则会保留在 rules 中供运行时做层级/行为解释；不会伪造不存在的业务关系。
    relations: List[Dict[str, Any]] = []
    for entity in ui_entities:
        if entity["id"] == root_id:
            continue
        relations.append(
            {
                "id": _stable_id("uirelation", [root_id, entity["id"], "contains"]),
                "type": "contains",
                "from": root_id,
                "to": entity["id"],
                "inferred": True,
            }
        )

    component_counts = Counter(entity["view"]["component"] for entity in ui_entities)
    type_counts = Counter(entity["entity_type"] for entity in ui_entities)
    renderer_counts = Counter(entity["view"]["renderer"] for entity in ui_entities)

    return {
        "schema": UI_SCHEMA,
        "root_id": root_id,
        "synthetic_root": synthetic_root,
        "entities": ui_entities,
        "relations": relations,
        "rules": all_rules,
        "global_rules": [rule["id"] for rule in compiled_global_rules],
        "registry": {
            "contract": "component-key -> renderer adapter",
            "namespaces": ["react", "three"],
        },
        "meta": {
            "entity_count": len(ui_entities),
            "rule_count": len(all_rules),
            "type_counts": dict(type_counts),
            "component_counts": dict(component_counts),
            "renderer_counts": dict(renderer_counts),
        },
    }


def build_data_context(payload: Any) -> Dict[str, Any]:
    """Normalize arbitrary backend JSON into a data context for UI binding.

    Entity-instancer packs are expanded here as well, so BlueNode/data may be
    connected directly to an instancer output without losing its effective
    rules before React/Three.js rendering.
    """
    raw = maybe_json(payload, payload)
    entities = _extract_entities(raw)
    if isinstance(raw, dict) and raw.get("kind") == "BLUE_ENTITY_INSTANCE_PACK":
        entities = collect_entities(raw)
    type_counts = Counter(_entity_type(entity) for entity in entities)

    if isinstance(raw, dict):
        top_level_keys = list(raw.keys())
    else:
        top_level_keys = []

    return {
        "schema": DATA_SCHEMA,
        "entities": entities,
        "raw": raw,
        "meta": {
            "entity_count": len(entities),
            "json_object_count": _recursive_json_object_count(raw),
            "type_counts": dict(type_counts),
            "top_level_keys": top_level_keys,
        },
    }
