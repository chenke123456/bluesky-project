# `blue_computation_node.py` — 基础计算节点

## 作用

`BlueComputationNode` 提供 BlueNode 内置的基础关系/场计算。它与 `BlueExecutorNode` 的专业分析程序不同：这里的逻辑直接写在节点文件里，主要生成关系摘要和简单场数据。

- 节点名：`计算`
- 分类：`Blue/Compute`
- 输入：可选 `BLUE_ENTITY_PACK`、`field_type`
- 当前 field 类型：`wind_field / magnetic_field / thermal_field / air_field / light_field / force_field / custom_field`

节点会：

1. 规范化实体包。
2. 计算 `pack_score()`。
3. 基于得分生成场强度。
4. 生成 `BLUE_RELATION_RESULT`。
5. 同时构造 `BLUE_FIELD` 数据。

## 关系结果

主要结构：

```json
{
  "kind": "BLUE_RELATION_RESULT",
  "payload": {
    "entities": [],
    "relations": [],
    "fields": {}
  },
  "meta": {
    "errors": []
  }
}
```

没有实体包时不会直接崩溃，而是在 `meta.errors` 中记录缺少 `JSON`。

## 当前实现注意事项

当前 `define_schema()` **只声明了一个 `BLUE_RELATION_RESULT` 输出**，但 `execute()` 实际执行：

```python
return io.NodeOutput(relation_result, field_data)
```

也就是返回两个值。文档按源码真实状态记录该差异；如果 ComfyUI 严格校验 schema/output 数量，应在代码层决定是补一个 `BLUE_FIELD.Output()`，还是只返回一个值。
