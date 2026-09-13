from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


DEVICE_OPTIONS = ["自动", "CPU", "GPU"]


def _torch_module():
    try:
        import torch  # type: ignore
        return torch
    except Exception:
        return None


def _cuda_info(torch: Any) -> Optional[Dict[str, Any]]:
    try:
        if not torch.cuda.is_available():
            return None
        index = int(torch.cuda.current_device())
        return {
            "kind": "gpu",
            "backend": "cuda",
            "torch_device": f"cuda:{index}",
            "index": index,
            "name": str(torch.cuda.get_device_name(index)),
        }
    except Exception:
        return None


def _mps_info(torch: Any) -> Optional[Dict[str, Any]]:
    try:
        backend = getattr(getattr(torch, "backends", None), "mps", None)
        if backend is None or not backend.is_available():
            return None
        return {
            "kind": "gpu",
            "backend": "mps",
            "torch_device": "mps",
            "index": None,
            "name": "Apple Metal (MPS)",
        }
    except Exception:
        return None


def available_gpu() -> Optional[Dict[str, Any]]:
    """返回当前可用 GPU 后端；优先 CUDA，其次 MPS。"""
    torch = _torch_module()
    if torch is None:
        return None
    return _cuda_info(torch) or _mps_info(torch)


def gpu_available() -> bool:
    return available_gpu() is not None


def resolve_device(mode: str = "自动") -> Dict[str, Any]:
    """把节点的 自动/CPU/GPU 选择解析为统一计算设备描述。

    - 自动：有 GPU 就使用 GPU，否则 CPU。
    - CPU：强制 CPU。
    - GPU：强制 GPU；没有可用 GPU 时明确报错，不静默回退。
    """
    raw = str(mode or "自动").strip()
    normalized = raw.lower()

    if raw == "CPU" or normalized == "cpu":
        return {
            "requested": raw,
            "kind": "cpu",
            "backend": "cpu",
            "torch_device": "cpu",
            "index": None,
            "name": "CPU",
        }

    gpu = available_gpu()

    if raw == "GPU" or normalized in {"gpu", "cuda", "mps"}:
        if gpu is None:
            raise RuntimeError("执行器选择了 GPU，但当前 Python 环境没有可用 CUDA/MPS GPU。")
        result = deepcopy(gpu)
        result["requested"] = raw
        return result

    # auto / 自动
    if gpu is not None:
        result = deepcopy(gpu)
        result["requested"] = raw
        return result

    return {
        "requested": raw,
        "kind": "cpu",
        "backend": "cpu",
        "torch_device": "cpu",
        "index": None,
        "name": "CPU",
    }


__all__ = ["DEVICE_OPTIONS", "available_gpu", "gpu_available", "resolve_device"]
