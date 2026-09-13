# `blue_prompt_booster_node.py` — 提示词提升器

## 作用

`BluePromptBoosterNode` 把 JSON、Schema 提示、语气要求和严格 JSON 约束组装成可发送给模型的文本。

- 节点名：`Blue 提示词提升器`
- 分类：`Blue/AI`
- 输入：`json_input`、`prompt_mode`、`schema_hint`、`tone_hint`、`strict_json`
- 输出：system text、prompt text、格式化 prompt pack JSON（三个字符串）

`prompt_mode` 可选：`system_only / prompt_only / both`。

## 输出语义

system text 固定强调 Blue 结构化数据、字段稳定和少解释；`strict_json = true` 时追加“输出必须是合法 JSON”。

prompt text 包含模式、Schema 和格式化后的输入数据。

第三个输出是：

```json
{
  "system_text": "...",
  "prompt_text": "...",
  "schema_hint": "...",
  "strict_json": true
}
```

## 边界

该节点**不调用任何在线大模型 API**，只负责构造提示词文本。实际模型调用应由其它 ComfyUI 节点或外部流程完成。
