from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


def normalize_json_document(value: Any) -> Dict[str, Any]:
    """将节点输入规范成可串联修改的 JSON object，并保留原始业务字段。"""
    if isinstance(value, dict):
        return deepcopy(value)

    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return deepcopy(parsed)
                if isinstance(parsed, list):
                    return {"entities": deepcopy(parsed)}
            except Exception:
                pass
        return {"value": value}

    if isinstance(value, (list, tuple)):
        return {"entities": deepcopy(list(value))}

    if value is None:
        return {}

    return {"value": deepcopy(value)}


def _as_rules(value: Any) -> List[Dict[str, Any]]:
    """Flatten BlueNode rule / rule-pack values without importing ComfyUI."""
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        result: List[Dict[str, Any]] = []
        for item in value:
            result.extend(_as_rules(item))
        return result

    if not isinstance(value, dict):
        return []

    if isinstance(value.get("rules"), list):
        return _as_rules(value["rules"])

    if value.get("kind") == "BLUE_RULE_PACK":
        payload = value.get("payload") if isinstance(value.get("payload"), dict) else {}
        return _as_rules(payload.get("rules", []))

    if value.get("rule_type") or value.get("name"):
        return [value]

    return []


def document_rules(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [deepcopy(rule) for rule in _as_rules(document.get("rules"))]


def entity_rules(entity: Any) -> List[Dict[str, Any]]:
    if not isinstance(entity, dict):
        return []

    direct = _as_rules(entity.get("rules"))
    if direct:
        return [deepcopy(rule) for rule in direct]

    # 兼容属性/方法分组格式；只有 rules 不存在时才回退，避免重复规则。
    result: List[Dict[str, Any]] = []
    result.extend(_as_rules(entity.get("properties")))
    result.extend(_as_rules(entity.get("methods")))
    return [deepcopy(rule) for rule in result]


def effective_rules(document: Dict[str, Any], entity: Any) -> List[Dict[str, Any]]:
    """全局规则在前、实体规则在后，因此 last-rule-wins 时实体规则优先。"""
    return document_rules(document) + entity_rules(entity)


def last_rule(
    rules: Iterable[Dict[str, Any]],
    rule_type: str,
    rule_name: str | None = None,
) -> Optional[Dict[str, Any]]:
    items = list(rules)
    for rule in reversed(items):
        if not isinstance(rule, dict):
            continue
        if rule.get("rule_type") == rule_type:
            return rule
        if rule_name and rule.get("name") == rule_name:
            return rule
    return None


def rule_params(rule: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(rule, dict):
        return {}
    params = rule.get("params")
    return deepcopy(params) if isinstance(params, dict) else {}


def _looks_like_entity(value: Dict[str, Any]) -> bool:
    return any(
        key in value
        for key in (
            "entity_id",
            "entity_name",
            "entity_item",
            "entity_category",
            "entity_type",
        )
    )


def execution_targets(document: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any]]]:
    """返回当前 JSON 中需要分析的实体；没有实体时仍允许执行全局规则。"""
    entities = document.get("entities")
    if isinstance(entities, list):
        return [
            (index, entity)
            for index, entity in enumerate(entities)
            if isinstance(entity, dict)
        ]

    entity = document.get("entity")
    if isinstance(entity, dict):
        return [(0, entity)]

    if _looks_like_entity(document):
        return [(0, document)]

    # 允许只有 rules 的分析请求；此时实体为空对象。
    return [(0, {})]


def entity_identity(entity: Dict[str, Any], index: int) -> Dict[str, Any]:
    identifier = (
        entity.get("id")
        or entity.get("entity_id")
        or entity.get("entity_name")
        or entity.get("entity_item")
        or f"entity_{index}"
    )
    name = (
        entity.get("entity_name")
        or entity.get("entity_item")
        or entity.get("name")
        or str(identifier)
    )
    return {
        "index": index,
        "id": str(identifier),
        "name": str(name),
    }


def ensure_results(document: Dict[str, Any]) -> Dict[str, Any]:
    results = document.get("results")
    if not isinstance(results, dict):
        results = {}
        document["results"] = results
    return results


def aggregate_status(statuses: Iterable[str]) -> str:
    values = [str(value) for value in statuses]
    if not values:
        return "blocked"
    if all(value == "completed" for value in values):
        return "completed"
    if all(value == "blocked" for value in values):
        return "blocked"
    if any(value == "blocked" for value in values):
        return "partial"
    if any(value == "configured" for value in values):
        return "configured"
    return values[-1]


def write_executor_result(
    document: Dict[str, Any],
    *,
    executor_key: str,
    executor_name: str,
    program: str,
    device: Dict[str, Any],
    status: str,
    items: List[Dict[str, Any]],
    messages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """只写自己的 results namespace，保留串联中其它执行器的结果。"""
    output = deepcopy(document)
    results = ensure_results(output)

    result = {
        "executor": {
            "key": executor_key,
            "name": executor_name,
            "program": program,
        },
        "device": deepcopy(device),
        "status": status,
        "items": deepcopy(items),
        "messages": list(messages or []),
    }
    results[executor_key] = result

    history = output.get("execution_history")
    if not isinstance(history, list):
        history = []
        output["execution_history"] = history
    history.append(
        {
            "executor": executor_key,
            "name": executor_name,
            "program": program,
            "device": deepcopy(device),
            "status": status,
            "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
    )
    return output


__all__ = [
    "aggregate_status",
    "effective_rules",
    "entity_identity",
    "execution_targets",
    "last_rule",
    "normalize_json_document",
    "rule_params",
    "write_executor_result",
]
