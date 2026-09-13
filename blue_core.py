import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from comfy_api.latest import io


BLUE_RULE = io.Custom("JSON")
BLUE_RULE_PACK = io.Custom("JSON")
BLUE_ENTITY = io.Custom("JSON")
BLUE_ENTITY_PACK = io.Custom("JSON")
BLUE_RELATION_RESULT = io.Custom("JSON")
BLUE_FIELD = io.Custom("JSON")
BLUE_JSON = io.Custom("JSON")
BLUE_WORLD = io.Custom("JSON")
BLUE_SIMULATION_SPEC = io.Custom("JSON")



RULE_NAME = [
    "color",
    "position",
    "position.2d",
    "position.3d",
    "layout.controls",
    "material",
    "strength",
    "stiffness",
    "time",
    "conduction",
    "growth",
    "scope",
    "topology",
    "collision",
    "load",
    "stability",
    "custom",
]

COLOR_OPTIONS = ["red", "green", "blue", "yellow", "black", "white", "custom"]
TOPOLOGY_OPTIONS = ["linear", "radial", "grid", "tree", "ring", "custom"]
ENTITY_TYPES = [
    "fan_part",
    "fan",
    "human",
    "house",
    "room",
    "door",
    "wall",
    "device",
    "machine",
    "furniture",
    "plant",
    "animal",
    "microbe",
    "weather",
    "custom",
]
FIELD_TYPES = [
    "wind_field",
    "magnetic_field",
    "thermal_field",
    "air_field",
    "light_field",
    "force_field",
    "custom_field",
]

RULE_SELECTOR_LABELS = {
    "color": ("颜色", "颜色 / 调色"),
    "position": ("位置", "坐标 / 方位"),
    "position.2d": ("二维位置", "矢量 (x, y)"),
    "position.3d": ("三维位置", "矢量 (x, y, z)"),
    "layout.controls": ("布局", "网站控件排列 / 对齐"),
    "material": ("材料", "材质 / 物性"),
    "strength": ("强度", "准则 / 安全系数"),
    "stiffness": ("刚度", "模型 / 位移限值"),
    "time": ("时间", "时间窗 / 周期"),
    "conduction": ("传导", "公式 / 路径"),
    "growth": ("生长", "阶段 / 速率"),
    "scope": ("作用域", "范围 / 层级"),
    "topology": ("拓扑", "连接 / 邻接"),
    "collision": ("冲突", "冲突对象 / 阈值"),
    "load": ("载荷", "受力 / 压力"),
    "stability": ("稳定性", "稳定阈值 / 风险"),
    "custom": ("自定义", "自定义值"),
}


def stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def pretty_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def maybe_json(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return json.loads(text)
        except Exception:
            return value
    return value


def to_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def split_tags(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).replace("\n", ",")
    return [piece.strip() for piece in text.split(",") if piece.strip()]


def combo_bool(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "enable", "enabled", "on"}


def clamp(num: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, num))


def default_rule_condition(rule_type: str, value: Any) -> Dict[str, Any]:
    if rule_type == "color":
        return {"color": value or "custom"}
    if rule_type == "topology":
        return {"topology": value or "custom"}
    if rule_type in {"position", "position.2d", "position.3d"}:
        return {"position": maybe_json(value, {})}
    if rule_type == "layout.controls":
        return {"layout": maybe_json(value, {})}
    if rule_type == "material":
        return {"material": maybe_json(value, {})}
    if rule_type == "time":
        return {"time": maybe_json(value, {})}
    if rule_type == "conduction":
        return {"formula": value or "default"}
    return {"value": maybe_json(value, value)}


def rule_selector(rule_type: str) -> Dict[str, str]:
    primary, secondary = RULE_SELECTOR_LABELS.get(rule_type, RULE_SELECTOR_LABELS["custom"])
    return {"primary": primary, "secondary": secondary}


def rule_weight(rule_type: str) -> float:
    return {
        "color": 0.05,
        "position": 0.10,
        "position.2d": 0.10,
        "position.3d": 0.10,
        "material": 0.15,
        "strength": 0.25,
        "stiffness": 0.25,
        "time": 0.10,
        "conduction": 0.25,
        "growth": 0.08,
        "scope": 0.10,
        "topology": 0.12,
        "collision": 0.18,
        "load": 0.20,
        "stability": 0.20,
        "custom": 0.10,
    }.get(rule_type, 0.10)


def entity_weight(entity_type: str) -> float:
    return {
        "fan_part": 0.72,
        "fan": 0.92,
        "human": 1.00,
        "house": 0.95,
        "room": 0.85,
        "door": 0.70,
        "wall": 0.75,
        "device": 0.86,
        "machine": 0.86,
        "furniture": 0.55,
        "plant": 0.58,
        "animal": 0.65,
        "microbe": 0.40,
        "weather": 0.80,
        "custom": 0.50,
    }.get(entity_type, 0.50)


def entity_position(entity: Dict[str, Any]) -> Tuple[float, float]:
    base = entity.get("base", {})
    position = base.get("position") or entity.get("position") or {}
    if isinstance(position, str):
        position = maybe_json(position, {})
    if isinstance(position, dict):
        x = position.get("x", position.get("left", 0.5))
        y = position.get("y", position.get("top", 0.5))
        try:
            return float(x), float(y)
        except Exception:
            pass
    return 0.5, 0.5


def normalize_rule(rule: Any) -> Optional[Dict[str, Any]]:
    if not rule:
        return None
    if isinstance(rule, dict):
        if rule.get("kind") == "BLUE_RULE":
            return rule
        rule_type = rule.get("rule_type", "custom")
        return {
            "id": rule.get("id") or stable_id("rule", rule),
            "kind": "BLUE_RULE",
            "rule_type": rule_type,
            "name": rule.get("name", "Rule"),
            "rule_name": rule.get("rule_name", rule.get("name", "Rule")),
            "scope": rule.get("scope", "global"),
            "priority": int(rule.get("priority", 50)),
            "enabled": bool(rule.get("enabled", True)),
            "target_tags": split_tags(rule.get("target_tags")),
            "payload": rule,
        }
    parsed = maybe_json(rule, None)
    if isinstance(parsed, dict):
        return normalize_rule(parsed)
    return None


def normalize_entity(entity: Any) -> Optional[Dict[str, Any]]:
    if not entity:
        return None
    if isinstance(entity, dict):
        if entity.get("kind") == "BLUE_ENTITY":
            return entity
        return {
            "id": entity.get("id") or stable_id("entity", entity),
            "kind": "BLUE_ENTITY",
            "entity_type": entity.get("entity_type", "custom"),
            "name": entity.get("name", "Entity"),
            "entity_name": entity.get("entity_name", entity.get("name", "Entity")),
            "scope": entity.get("scope", "module"),
            "base": entity,
        }
    parsed = maybe_json(entity, None)
    if isinstance(parsed, dict):
        return normalize_entity(parsed)
    return None


def normalize_rule_pack(pack: Any) -> Optional[Dict[str, Any]]:
    if not pack:
        return None
    if isinstance(pack, dict) and pack.get("kind") == "BLUE_RULE_PACK":
        return pack
    parsed = maybe_json(pack, None)
    if isinstance(parsed, dict):
        return normalize_rule_pack(parsed)
    return None


def normalize_entity_pack(pack: Any, _depth: int = 0) -> Optional[Dict[str, Any]]:
    """规范化实体包，带有递归深度保护"""
    # 防止无限递归
    if _depth > 10:  # 最大递归深度限制
        print(f"[normalize_entity_pack] 达到最大递归深度，停止处理")
        return None

    if not pack:
        return None

    # 如果已经是有效的实体包，直接返回
    if isinstance(pack, dict) and pack.get("kind") == "BLUE_ENTITY_PACK":
        return pack

    # 尝试解析 JSON
    parsed = maybe_json(pack, None)

    # 如果解析后是字典，且与原始输入不同，递归处理（增加深度计数）
    if isinstance(parsed, dict) and parsed is not pack:
        return normalize_entity_pack(parsed, _depth + 1)

    # 如果解析后是字典但可能与原始输入相同，直接返回
    if isinstance(parsed, dict):
        return parsed

    return None


def collect_rules(*candidates: Any) -> List[Dict[str, Any]]:
    """收集规则，并兼容 dict / list / 旧版 JSON 字符串。

    规则包内部的 ``rules``、实体实例器的 ``instance_rules`` 以及实体自身的
    ``rules`` 都是列表。这里必须递归展开 list/tuple；否则实例器在物化时把
    整个列表作为一个 candidate 传入，会静默得到空规则，导致实例覆盖规则
    丢失并让 World 回退到类型默认值（例如 machine 的黄色）。
    """
    rules: List[Dict[str, Any]] = []
    for candidate in candidates:
        if not candidate:
            continue

        candidate = maybe_json(candidate, candidate)

        # 规则列表是 BlueNode 内部的标准结构。递归展开，既支持调用方传
        # collect_rules(rule_list)，也支持 collect_rules(*rule_list)。
        if isinstance(candidate, (list, tuple)):
            rules.extend(collect_rules(*candidate))
            continue

        if isinstance(candidate, dict) and candidate.get("kind") == "BLUE_RULE_PACK":
            nested = candidate.get("payload", {}).get("rules", [])
            rules.extend(collect_rules(nested))
            continue

        # 当前简化规则包：{"rules": [...]}
        if isinstance(candidate, dict) and isinstance(candidate.get("rules"), list):
            rules.extend(collect_rules(candidate["rules"]))
            continue

        if isinstance(candidate, dict):
            rules.append(candidate)

    return rules


def collect_entities(*candidates: Any) -> List[Dict[str, Any]]:
    """收集实体，并兼容旧版节点产生的 JSON 字符串。"""
    entities: List[Dict[str, Any]] = []
    for candidate in candidates:
        if not candidate:
            continue

        candidate = maybe_json(candidate, candidate)

        if isinstance(candidate, dict) and candidate.get("kind") == "BLUE_ENTITY_PACK":
            nested = candidate.get("payload", {}).get("entities", [])
            entities.extend(collect_entities(*to_list(nested)))
            continue

        # 实体实例器保持“模板 + 差异”紧凑结构；只有下游真正需要实体列表时才展开。
        if isinstance(candidate, dict) and candidate.get("kind") == "BLUE_ENTITY_INSTANCE_PACK":
            try:
                from .blue_entity_instancer_node import materialize_instance_pack
                entities.extend(materialize_instance_pack(candidate))
            except Exception as exc:
                print(f"[collect_entities] 实例包展开失败: {exc}")
            continue

        # 当前简化实体包：{"entities": [...]}
        if isinstance(candidate, dict) and isinstance(candidate.get("entities"), list):
            entities.extend(collect_entities(*candidate["entities"]))
            continue

        if isinstance(candidate, dict):
            # 兼容旧版实体结构 {"name": ..., "rule": "{...}"}
            # 在这里顺手升级成 {"name": ..., "rules": [...]}。
            if "rules" not in candidate and "rule" in candidate:
                old_rule = maybe_json(candidate.get("rule"), candidate.get("rule"))
                if isinstance(old_rule, dict) and isinstance(old_rule.get("rules"), list):
                    candidate = dict(candidate)
                    candidate.pop("rule", None)
                    candidate["rules"] = collect_rules(*old_rule["rules"])
                elif old_rule:
                    candidate = dict(candidate)
                    candidate.pop("rule", None)
                    candidate["rules"] = collect_rules(old_rule)
            entities.append(candidate)

    return entities


def make_entity(
    entity_type: str,
    entity_name: str,
    scope: str,
    part_of: str,
    position_json: Any,
    geometry_json: Any,
    state_json: Any,
    materials_json: Any,
    tags: List[str],
    attached_rule_pack: Optional[Dict[str, Any]],
    notes: str,
) -> Dict[str, Any]:
    position = maybe_json(position_json, {})
    geometry = maybe_json(geometry_json, {})
    state = maybe_json(state_json, {})
    materials = maybe_json(materials_json, {})
    attached_rules = []
    attached_rule_pack_id = None
    if attached_rule_pack:
        attached_rule_pack_id = attached_rule_pack.get("id")
        attached_rules = to_list(attached_rule_pack.get("payload", {}).get("rules", []))
    return {
        "id": stable_id(
            "entity",
            {
                "type": entity_type,
                "name": entity_name,
                "scope": scope,
                "part_of": part_of,
                "position": position,
                "geometry": geometry,
                "state": state,
                "materials": materials,
                "tags": tags,
                "attached_rule_pack_id": attached_rule_pack_id,
            },
        ),
        "kind": "BLUE_ENTITY",
        "entity_type": entity_type,
        "name": entity_name,
        "entity_name": entity_name,
        "scope": scope,
        "part_of": part_of,
        "position": position if isinstance(position, (dict, list)) else {"raw": position},
        "geometry": geometry if isinstance(geometry, (dict, list)) else {"raw": geometry},
        "state": state if isinstance(state, (dict, list)) else {"raw": state},
        "materials": materials if isinstance(materials, (dict, list)) else {"raw": materials},
        "tags": tags,
        "rules": attached_rules,
        "attached_rule_pack_id": attached_rule_pack_id,
        "notes": notes or "",
        "meta": {"source": "BlueEntityNode"},
    }


def local_entity_score(entity: Dict[str, Any]) -> float:
    base = entity_weight(entity.get("entity_type", "custom"))
    attached_rules = to_list(entity.get("rules", []))
    if not attached_rules:
        return base * 0.2
    rule_sum = 0.0
    for rule in attached_rules:
        rule = normalize_rule(rule)
        if not rule:
            continue
        rule_sum += rule_weight(rule.get("rule_type", "custom")) * (rule.get("priority", 50) / 100.0)
    return clamp(base * (0.25 + rule_sum / max(1, len(attached_rules))))


def pack_score(entities: Sequence[Dict[str, Any]]) -> float:
    if not entities:
        return 0.0
    return clamp(sum(local_entity_score(entity) for entity in entities) / len(entities))


def rule_pack_score(rules: Sequence[Dict[str, Any]]) -> float:
    if not rules:
        return 0.0
    scores = []
    for rule in rules:
        rule = normalize_rule(rule)
        if not rule:
            continue
        score = rule_weight(rule.get("rule_type", "custom")) * (rule.get("priority", 50) / 100.0)
        if rule.get("scope", "global") != "global":
            score *= 1.1
        if not rule.get("enabled", True):
            score *= 0.25
        scores.append(score)
    return clamp(sum(scores) / max(1, len(scores)))


def render_text(image: Image.Image, title: str, lines: List[str], box=(16, 16), color=(255, 255, 255)) -> None:
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    x, y = box
    draw.text((x, y), title, fill=color, font=font)
    y += 18
    for line in lines:
        draw.text((x, y), line, fill=color, font=font)
        y += 14


def pil_to_tensor(image: Image.Image) -> torch.Tensor:
    arr = np.array(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]
