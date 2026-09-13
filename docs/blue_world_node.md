# `blue_world_node.py` — 世界节点

## 作用

`BlueWorldNode` 把实体与规则编译成一份**静态世界定义**。它不启动模拟，不创建 tick loop，也不负责业务实体的三维尺寸设计。

- 节点名：`世界`
- 分类：`Blue/Simulation`
- 输入：可选实体包、可选规则包、`world_name`
- 输出：`BLUE_WORLD`

## 输出结构

```json
{
  "kind": "BLUE_WORLD",
  "name": "city",
  "tick": 0,
  "time": 0.0,
  "entities": [],
  "rules": []
}
```

## 实体状态编译

`_compile_entity_state()` 会 deepcopy 实体，并补充运行时兼容状态：

- 缺少 `id` 时生成稳定 ID。
- 缺少 `transform` 时提供兼容 fallback 位置和零旋转。
- 缺少 `motion` 时补零速度。
- 缺少 `interaction` 时补选择/动作能力。
- 将最终生效的颜色规则落成 `appearance.color`。

颜色优先级：

```text
实体规则中的最后一个颜色规则
  > 已显式存在的 appearance.color
  > entity_type 默认色
```

## 几何边界

World 不把 `绘图规则 / 尺寸规则 / 三维位置规则` 编译成另一套几何描述，也不会根据实体名称创造尺寸。规则原样保留给 Three.js Selector / Runtime 解释。

代码会移除旧式 `render_spec`，避免 World 成为第二套三维几何源。

## 与模拟/网页的关系

```text
实体包 + 规则包
      -> 世界
      -> 模拟（只生成配置）
      -> HTML 输出（作为 data stream）
```

World 是静态初始状态，不等于正在运行的 Simulation Runtime。
