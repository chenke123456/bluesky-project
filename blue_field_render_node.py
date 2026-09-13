from PIL import Image
from comfy_api.latest import io

from .blue_core import BLUE_FIELD, pil_to_tensor, render_text, maybe_json


class BlueFieldRenderNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueFieldRenderNode",
            display_name="渲染",
            category="Blue/Visualization",
            inputs=[
                BLUE_FIELD.Input("JSON", optional=True),
                io.Combo.Input("render_mode", options=["heatmap", "arrows", "both"]),
                io.String.Input("palette", default="blue", multiline=False),
                io.Int.Input("resolution", default=512, min=128, max=2048, step=64),
            ],
            outputs=[io.Image.Output()],
        )

    @classmethod
    def execute(cls, JSON=None, render_mode="both", palette="blue", resolution=512) -> io.NodeOutput:
        field = JSON if isinstance(JSON, dict) else maybe_json(JSON, {})
        data = field.get("data", {}) if isinstance(field, dict) else {}
        speed = float(data.get("speed", data.get("intensity", 1.0)))
        coverage = float(data.get("coverage", 0.5))
        size = int(resolution)
        image = Image.new("RGB", (size, size), (14, 18, 24))
        render_text(
            image,
            "Wind Field",
            [
                f"speed={round(speed, 3)}",
                f"coverage={round(coverage, 3)}",
                f"palette={palette}",
            ],
            box=(18, 18),
            color=(255, 255, 255),
        )
        return io.NodeOutput(pil_to_tensor(image))
