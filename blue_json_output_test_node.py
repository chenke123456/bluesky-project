from comfy_api.latest import io

from .blue_core import BLUE_JSON, maybe_json, pretty_json


class BlueJsonOutputTestNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueJsonOutputTestNode",
            display_name="Blue JSON 输出测试",
            category="Blue/JSON",
            inputs=[
                io.String.Input("json_text", default='{"hello":"blue"}', multiline=True),
            ],
            outputs=[
                BLUE_JSON.Output(),
                io.String.Output(),
            ],
        )

    @classmethod
    def execute(cls, json_text='{"hello":"blue"}') -> io.NodeOutput:
        payload = maybe_json(json_text, json_text)
        display = pretty_json(payload) if isinstance(payload, (dict, list)) else str(payload)
        return io.NodeOutput(payload, display)
