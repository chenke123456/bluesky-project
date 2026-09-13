# `blue_executor_node.py` — 统一执行器节点

## 作用

`BlueExecutorNode` 是专业工程/数值分析程序的统一调度入口，接口固定为：

```text
BLUE_JSON -> Executor + Device -> BLUE_JSON
```

- 节点名：`执行器`
- 分类：`Blue/Executors`
- 输入：`JSON`、执行器、设备。
- 输出：`BLUE_JSON`

Three.js 是浏览器渲染器，不属于这里的执行器列表。

## 当前执行器

`executors/__init__.py` 当前注册：

- 强度分析：`strength_executor.py`
- 刚度分析：`stiffness_executor.py`

节点通过 `get_executor()` 获取函数，再以统一形式调用：

```python
program(JSON, device=compute_device)
```

## 数据处理原则

`executors/common.py` 提供通用行为：

- `normalize_json_document()`：尽量保留原业务 JSON，只规范成可修改 object。
- `effective_rules()`：规则优先级为全局规则 -> 实体规则，因此 last-rule-wins 的执行器可以让局部规则覆盖全局规则。
- `execution_targets()`：优先逐实体执行；单实体输入直接作为目标；没有实体时仍可按全局文档执行。
- `write_executor_result()`：只写当前执行器的结果命名空间。

串联示例：

```text
JSON
  -> 强度分析
  -> JSON(results.strength)
  -> 刚度分析
  -> JSON(results.strength + results.stiffness)
```

执行器不应删除已有字段，也不应覆盖其他执行器的 `results.*`。

## Device

`executors/device.py` 支持：

- `自动`
- `CPU`
- `GPU`

自动探测顺序：

```text
CUDA -> MPS -> CPU
```

强制 GPU 但没有可用 CUDA/MPS 时会报错。统一设备描述中可包含 `kind / backend / torch_device / name`，方便未来真实数值求解器或 Torch 模型使用。

## 当前强度 / 刚度边界

当前实现以规则分析和 `analysis_request` 为主，不伪造不存在的有限元结果。专业求解逻辑应继续放在各自 executor 文件中，而不是堆进 `BlueExecutorNode`。

## 新增执行器

新建 `executors/<name>_executor.py`：

```python
EXECUTOR_NAME = "热分析"
PROGRAM = "thermal"


def execute(JSON, *, device):
    ...
```

然后在 `executors/__init__.py` 注册。推荐复用：

- `normalize_json_document`
- `execution_targets`
- `effective_rules`
- `last_rule`
- `rule_params`
- `entity_identity`
- `aggregate_status`
- `write_executor_result`

这样才能保持执行器的规则优先级和串联语义一致。
