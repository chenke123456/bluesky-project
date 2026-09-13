from __future__ import annotations

from typing import Any, Dict, List

from .common import (
    aggregate_status,
    effective_rules,
    entity_identity,
    execution_targets,
    last_rule,
    normalize_json_document,
    rule_params,
    write_executor_result,
)

EXECUTOR_KEY = "strength"
EXECUTOR_NAME = "强度执行器"
PROGRAM = "executors/strength_executor.py"


def _analyze_entity(
    document: Dict[str, Any],
    entity: Dict[str, Any],
    index: int,
    device: Dict[str, Any],
) -> Dict[str, Any]:
    rules = effective_rules(document, entity)
    strength_rule = last_rule(rules, "strength", "强度规则")
    material_rule = last_rule(rules, "material", "材料规则")
    load_rule = last_rule(rules, "load", "载荷规则")
    size_rule = last_rule(rules, "geometry.size", "尺寸规则")
    constraint_rule = last_rule(rules, "constraint", "约束规则")

    definition = rule_params(strength_rule)
    supplied_result = definition.get("result") if isinstance(definition.get("result"), dict) else None

    request = {
        "definition": definition,
        "material": rule_params(material_rule),
        "load": rule_params(load_rule),
        "size": rule_params(size_rule),
        "constraint": rule_params(constraint_rule),
        "compute_device": device.get("torch_device", "cpu"),
    }

    identity = entity_identity(entity, index)

    if not strength_rule:
        return {
            **identity,
            "status": "blocked",
            "missing": ["strength"],
            "analysis_request": request,
            "data": None,
        }

    if supplied_result:
        return {
            **identity,
            "status": "completed",
            "missing": [],
            "analysis_request": request,
            "data": supplied_result,
        }

    # 这里是数值求解程序的稳定入口。未来把 FEA/矩阵求解接到这里，
    # 并使用 device['torch_device'] 决定 CPU/CUDA/MPS。
    return {
        **identity,
        "status": "configured",
        "missing": [],
        "analysis_request": request,
        "data": None,
    }


def execute(JSON: Any, *, device: Dict[str, Any]) -> Dict[str, Any]:
    """执行强度分析程序，并把结果追加到 JSON.results.strength。

    当前版本负责规则筛选、设备选择和求解边界，不伪造有限元应力值。
    """
    document = normalize_json_document(JSON)
    items: List[Dict[str, Any]] = [
        _analyze_entity(document, entity, index, device)
        for index, entity in execution_targets(document)
    ]
    status = aggregate_status(item.get("status", "blocked") for item in items)

    messages = []
    if status in {"configured", "partial"}:
        messages.append(
            "强度执行器已进入数值求解边界；当前未接入具体 FEA 求解器，因此只生成 analysis_request。"
        )
    if status == "blocked":
        messages.append("缺少强度规则 strength，强度计算未执行。")

    return write_executor_result(
        document,
        executor_key=EXECUTOR_KEY,
        executor_name=EXECUTOR_NAME,
        program=PROGRAM,
        device=device,
        status=status,
        items=items,
        messages=messages,
    )
