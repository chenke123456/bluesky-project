from __future__ import annotations

from comfy_api.latest import io

from .blue_core import BLUE_JSON
from .executors import EXECUTOR_OPTIONS, get_executor
from .executors.device import DEVICE_OPTIONS, resolve_device


class BlueExecutorNode(io.ComfyNode):
    """统一计算执行器节点。

    工作流接口固定为 JSON -> Executor -> JSON。
    Three.js 不属于这里的计算执行器；浏览器运行时会直接读取 JSON 中的
    entities/rules/results 进行选择和渲染。
    """

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueExecutorNode",
            display_name="执行器",
            category="Blue/Executors",
            inputs=[
                BLUE_JSON.Input("JSON"),
                io.Combo.Input(
                    "executor",
                    options=EXECUTOR_OPTIONS,
                    default=EXECUTOR_OPTIONS[0],
                ),
                io.Combo.Input(
                    "device",
                    options=DEVICE_OPTIONS,
                    default=DEVICE_OPTIONS[0],
                ),
            ],
            outputs=[
                BLUE_JSON.Output(display_name="JSON"),
            ],
        )

    @classmethod
    def execute(cls, JSON, executor=EXECUTOR_OPTIONS[0], device=DEVICE_OPTIONS[0]) -> io.NodeOutput:
        compute_device = resolve_device(device)
        program = get_executor(executor)
        result = program(JSON, device=compute_device)
        return io.NodeOutput(result)
