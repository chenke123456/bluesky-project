from comfy_api.latest import io

from .blue_core import maybe_json, pretty_json


class BluePromptBoosterNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BluePromptBoosterNode",
            display_name="Blue 提示词提升器",
            category="Blue/AI",
            inputs=[
                io.String.Input("json_input", default="", multiline=True),
                io.Combo.Input("prompt_mode", options=["system_only", "prompt_only", "both"]),
                io.String.Input("schema_hint", default="", multiline=True),
                io.String.Input("tone_hint", default="只输出 JSON，不要解释。", multiline=True),
                io.Combo.Input("strict_json", options=["true", "false"]),
            ],
            outputs=[
                io.String.Output(),
                io.String.Output(),
                io.String.Output(),
            ],
        )

    @classmethod
    def execute(cls, json_input, prompt_mode, schema_hint, tone_hint, strict_json) -> io.NodeOutput:
        payload = maybe_json(json_input, json_input)
        payload_text = pretty_json(payload) if isinstance(payload, (dict, list)) else str(payload)
        system_text = "\n".join([
            "你是 Blue 的结构化数据提升器。",
            tone_hint or "只输出 JSON。",
            "请保持字段稳定，避免解释性文本。",
        ])
        if strict_json == "true":
            system_text += "\n输出必须是合法 JSON。"
        prompt_text = "\n".join([
            f"模式: {prompt_mode}",
            f"Schema: {schema_hint}",
            "输入数据:",
            payload_text,
        ])
        prompt_pack = {
            "system_text": system_text,
            "prompt_text": prompt_text,
            "schema_hint": schema_hint,
            "strict_json": strict_json == "true",
        }
        return io.NodeOutput(system_text, prompt_text, pretty_json(prompt_pack))
