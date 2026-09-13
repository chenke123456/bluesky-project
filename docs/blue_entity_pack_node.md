# `blue_entity_pack_node.py` — 实体包节点

## 作用

`BlueEntityPackNode` 把多个实体收集成统一实体包，供 World、计算、平面图、Executor 等下游使用。

- 节点名：`实体包`
- 分类：`Blue/Entities`
- 输入：最多 24 个可选 `BLUE_ENTITY`
- 输出：`BLUE_ENTITY_PACK`

输出保持简单：

```json
{
  "entities": []
}
```

收集过程使用 `blue_core.collect_entities()`，负责兼容单实体、普通实体包和实例器生成的实例包等形式。

本节点只聚合数据，不修改实体规则、位置、几何或显示逻辑。
