# `blue_simulation_node.py` — 模拟节点

## 作用

`BlueSimulationNode` 只生成模拟配置规格，不启动实际服务器端模拟循环。

- 节点名：`模拟`
- 分类：`Blue/Simulation`
- 输入：`BLUE_WORLD`、`tick_rate`、五个系统开关
- 输出：`BLUE_SIMULATION_SPEC`

系统开关：movement、traffic、citizen、economy、power。

## 输出结构

```json
{
  "kind": "BLUE_SIMULATION_SPEC",
  "world": {},
  "entities": [],
  "rules": [],
  "config": {
    "tick_rate": 20,
    "systems": ["movement", "traffic"]
  },
  "runtime": {
    "created": false,
    "running": false
  }
}
```

`entities / rules` 是为了兼容现有 data -> UI 链路保留的别名。

## 重要边界

当前实现明确不会：

- 创建后台线程。
- 创建 simulation session。
- 启动 tick loop。
- 持续更新实体 transform。
- 让实体因为 movement 开关而自动运动。

所以 `tick_rate` 和 `systems` 当前是**配置描述**，不是已启动的运行时。

如果以后实现真实 Runtime，应独立设计生命周期、取消机制、工作流 session 隔离和资源回收，不建议直接在 `execute()` 内启动永久后台线程。
