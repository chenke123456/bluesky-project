# `blue_rule_pack_node.py` — 规则包节点

## 作用

`BlueRulePackNode` 把多条 `BLUE_RULE` 聚合成一个规则包。

- 节点名：`规则包`
- 分类：`Blue/Rules`
- 输入：最多 24 个可选 `BLUE_RULE`
- 输出：`BLUE_RULE_PACK`

节点不解释规则内容，只负责收集并按属性/方法分组。

## 输出结构

```json
{
  "properties": [],
  "methods": [],
  "rules": []
}
```

- `properties`：`rule_kind != method` 的规则。
- `methods`：`rule_kind == method` 的规则。
- `rules`：扁平兼容列表，供现有 World / UI / Simulation 等消费链路继续使用。

收集过程使用 `blue_core.collect_rules()`，因此可以兼容项目当前允许的 dict、list/tuple 以及旧 JSON 字符串形式。

## 使用位置

常见连接：

```text
规则 -> 规则包 -> 实体
规则 -> 规则包 -> 实体实例器（实例规则）
规则 -> 规则包 -> 世界（全局规则）
```

规则优先级由下游决定；本节点不主动去重或覆盖同类规则。
