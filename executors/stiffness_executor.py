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

EXECUTOR_KEY = "stiffness"
EXECUTOR_NAME = "刚度执行器"
PROGRAM = "executors/stiffness_executor.py"


def _analyze_entity(
    document: Dict[str, Any],
    entity: Dict[str, Any],
    index: int,
    device: Dict[str, Any],
) -> Dict[str, Any]:
    rules = effective_rules(document, entity)
    stiffness_rule = last_rule(rules, "stiffness", "刚度规则")
    material_rule = last_rule(rules, "material", "材料规则")
    load_rule = last_rule(rules, "load", "载荷规则")
    size_rule = last_rule(rules, "geometry.size", "尺寸规则")
    constraint_rule = last_rule(rules, "constraint", "约束规则")

    definition = rule_params(stiffness_rule)
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

    if not stiffness_rule:
        return {
            **identity,
            "status": "blocked",
            "missing": ["stiffness"],
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

    # 未来的位移/变形/刚度矩阵求解放在这里；执行设备由 device.py 统一选择。
    return {
        **identity,
        "status": "configured",
        "missing": [],
        "analysis_request": request,
        "data": None,
    }


def execute(JSON: Any, *, device: Dict[str, Any]) -> Dict[str, Any]:
    """执行刚度分析程序，并把结果追加到 JSON.results.stiffness。"""
    document = normalize_json_document(JSON)
    items: List[Dict[str, Any]] = [
        _analyze_entity(document, entity, index, device)
        for index, entity in execution_targets(document)
    ]
    status = aggregate_status(item.get("status", "blocked") for item in items)

    messages = []
    if status in {"configured", "partial"}:
        messages.append(
            "刚度执行器已进入数值求解边界；当前未接入具体结构求解器，因此只生成 analysis_request。"
        )
    if status == "blocked":
        messages.append("缺少刚度规则 stiffness，刚度计算未执行。")

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
