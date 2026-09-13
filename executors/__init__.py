from __future__ import annotations

from typing import Callable, Dict

from . import stiffness_executor, strength_executor

EXECUTOR_OPTIONS = [
    strength_executor.EXECUTOR_NAME,
    stiffness_executor.EXECUTOR_NAME,
]

_EXECUTOR_REGISTRY: Dict[str, Callable[..., dict]] = {
    strength_executor.EXECUTOR_NAME: strength_executor.execute,
    stiffness_executor.EXECUTOR_NAME: stiffness_executor.execute,
}


def get_executor(name: str) -> Callable[..., dict]:
    try:
        return _EXECUTOR_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"未知执行器: {name}") from exc


def executor_programs() -> Dict[str, str]:
    return {
        strength_executor.EXECUTOR_NAME: strength_executor.PROGRAM,
        stiffness_executor.EXECUTOR_NAME: stiffness_executor.PROGRAM,
    }


__all__ = ["EXECUTOR_OPTIONS", "get_executor", "executor_programs"]
