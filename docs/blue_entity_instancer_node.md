# `blue_entity_instancer_node.py` — 实体实例器

## 作用

`BlueEntityInstancerNode` 从一个实体模板生成大量实例，并以紧凑实例包保存模板、覆盖规则和每个实例的 transform。

- 节点名：`实体实例器`
- 分类：`Blue/Entities`
- 输入：实体模板、可选实例规则、数量、排列/命名参数。
- 输出：`BLUE_ENTITY_PACK`（内容为 `BLUE_ENTITY_INSTANCE_PACK`）。

## 输入

- `实体模板`：一个 `BLUE_ENTITY`。
- `实例规则`：可选 `BLUE_RULE_PACK`，作为实例级最高优先级覆盖。
- `数量`：1–10000。
- `排列模式`：线性、网格、圆周、重叠。
- `命名规则`：默认 `{name}_{index}`。
- 起点 XYZ、间距 XYZ。
- 网格 `每行数量`。
- 圆周半径、起始角度、总角度。

这些排列参数描述“如何生成实例”，所以属于实例器自身，而不是实体属性规则。

## 输出结构

```json
{
  "kind": "BLUE_ENTITY_INSTANCE_PACK",
  "template_id": "...",
  "template": {},
  "count": 10,
  "instance_rules": [],
  "instances": [
    {
      "id": "...",
      "index": 0,
      "name": "...",
      "transform": {
        "position": {"x": 0, "y": 0, "z": 0},
        "rotation": {"x": 0, "y": 0, "z": 0}
      }
    }
  ]
}
```

紧凑包不会为每个实例重复整份实体模板；下游需要实体列表时使用 `materialize_instance_pack()` 展开。

## 命名与实例变量

字符串规则值可以使用：

- `{index}`：从 0 开始。
- `{index1}`：从 1 开始。
- `{count}`：总实例数。
- `{name}`：当前实例名称。

主要用于自定义属性/方法规则中的实例参数化。

## 规则覆盖

模板规则与 `实例规则` 使用 last-writer-wins 语义：相同 `rule_kind + rule_type` 时，实例规则替换模板已有同类规则；不同类型继续共存。

展开后每个实例会重新生成：

- `rules`
- `properties`
- `methods`
- `transform`
- `instance_of`
- `instance_index`

`collect_rules()` 可递归处理 list/tuple，因此紧凑包中的 `template.rules` / `instance_rules` 不会在物化时被静默丢弃。
