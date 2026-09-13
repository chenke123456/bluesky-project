from __future__ import annotations

from comfy_api.latest import io

from .blue_core import BLUE_SIMULATION_SPEC, BLUE_WORLD


TOGGLE = ["启用", "关闭"]


class BlueSimulationNode(io.ComfyNode):
    """Describe simulation configuration only. No thread, session, tick loop or movement is started."""

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueSimulationNode",
            display_name="模拟",
            category="Blue/Simulation",
            inputs=[
                BLUE_WORLD.Input("world"),
                io.Int.Input("tick_rate", default=20, min=1, max=120, step=1),
                io.Combo.Input("movement", options=TOGGLE),
                io.Combo.Input("traffic", options=TOGGLE),
                io.Combo.Input("citizen", options=TOGGLE),
                io.Combo.Input("economy", options=TOGGLE),
                io.Combo.Input("power", options=TOGGLE),
            ],
            outputs=[BLUE_SIMULATION_SPEC.Output(display_name="JSON")],
        )

    @classmethod
    def execute(
        cls, world, tick_rate=20, movement="启用", traffic="启用",
        citizen="启用", economy="启用", power="启用",
    ) -> io.NodeOutput:
        systems = []
        if movement == "启用":
            systems.append("movement")
        if traffic == "启用":
            systems.append("traffic")
        if citizen == "启用":
            systems.append("citizen")
        if economy == "启用":
            systems.append("economy")
        if power == "启用":
            systems.append("power")

        entities = world.get("entities", []) if isinstance(world, dict) else []
        rules = world.get("rules", []) if isinstance(world, dict) else []
        spec = {
            "kind": "BLUE_SIMULATION_SPEC",
            "world": world,
            # Compatibility aliases for the existing BlueNode/data -> UI pipeline.
            "entities": entities,
            "rules": rules,
            "config": {"tick_rate": int(tick_rate), "systems": systems},
            "runtime": {"created": False, "running": False},
        }
        return io.NodeOutput(spec)
