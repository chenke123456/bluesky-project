# BlueNode 开发与文档约定

## 文档约定

新增或修改一个 `blue_*_node.py` 节点时，同步维护同名文档：

```text
blue_xxx_node.py
  <-> docs/blue_xxx_node.md
```

不要再为同一个节点的单个规则或小修复新建一批顶层专题文档；应把稳定行为合并回节点文档。跨节点、短期补丁说明优先写代码注释、提交记录或 issue，避免 `docs/` 再次碎片化。

## 新增 ComfyUI 节点

最小结构：

```python
from comfy_api.latest import io


class MyBlueNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="MyBlueNode",
            display_name="我的节点",
            category="Blue/...",
            inputs=[...],
            outputs=[...],
        )

    @classmethod
    def execute(cls, ...):
        return io.NodeOutput(...)
```

然后在根目录 `__init__.py` import 并加入 `BlueNodeExtension.get_node_list()`；只新增 Python 文件不会自动注册节点。

新增节点时尽量保持职责清楚，并优先接入现有 Rule、Entity、Executor、World、Simulation 和输出数据流，使新节点能与已有节点组合，而不是建立一条独立的数据链。

## 复用 `blue_core.py`

节点优先复用：

- `collect_rules()` / `collect_entities()`
- `normalize_rule*()` / `normalize_entity*()`
- `stable_id()`
- `maybe_json()` / `pretty_json()`

项目当前需要兼容 dict、list/tuple 和部分旧 JSON 字符串输入，不建议每个节点重复写一套解析逻辑。

## 新增实体 / 规则

新增实体时同时检查：类别、item、后端 category/item 校验、entity type/geometry 映射，以及是否真的是网站 UI 实体。

新增专业对象时优先继续使用现有实体结构和稳定 ID，使对象仍然可以被 Rule、Executor、World、Simulation 和输出节点引用。

新增规则时同步处理：规则名、属性/方法归类、`rule_type`、动态输入数量、`_compile_params()` 和下游 Runtime / Executor 的消费逻辑。

新增专业约束时优先扩展 `规则` / `规则包` 以及下游读取逻辑，不要为每一种专业规则再建立一套互不兼容的约束格式。

## 新增 Executor

保持统一接口：

```python
def execute(JSON, *, device):
    ...
```

保留原 JSON，只写自己的 `results.<namespace>`，并复用 `executors/common.py` 的规则优先级和 target 选择逻辑。这样机械、建筑、装修、灾害等不同专业 Executor 可以连续作用在同一份方案数据上，而不用覆盖彼此结果。

详见 [`blue_executor_node.md`](blue_executor_node.md)。

## AI 相关扩展

如果以后增加自动生成候选方案、参数建议或方案迭代，输出应尽量回到现有 Blue JSON、Rule、Entity、Executor、World 和 Simulation 数据结构，再进入后续计算链。不要建立只能由 AI 使用、无法与现有节点互通的第二套方案格式。

## 修改网页链路

按职责修改：

- 数据投影：`blue_ui_model.py`
- HTML shell：`blue_ui_compiler.py`
- 文件输出/插件判断：`blue_html_output_node.py`
- 站点有效性：`blue_site_state.py`
- HTTP：`blue_http_routes.py`
- 浏览器行为：`html/runtime.js`
- 浏览器样式：`html/runtime.css`

不要把所有逻辑重新堆回 HTML 输出节点。

## 模拟系统

当前 `BlueWorldNode` 是静态 World 编译，`BlueSimulationNode` 是 Simulation Spec 编译。真实 tick runtime 尚不存在。

未来实现真实仿真时应继续沿 World / Simulation Spec 边界扩展，并独立处理生命周期、取消、session 隔离和资源回收，使现有实体、规则和 Executor 结果仍能进入同一模拟链路。

## 结果与评估扩展

新增成本、安全、舒适度、生态、施工性等评估能力时，优先保留各自结果字段，不要过早压缩成单一总分。这样同一方案可以做多维比较，也可以替换其中一个实体、规则或专业参数后只重新运行受影响的后续步骤。

## 基础检查

Python 修改后至少运行：

```bash
python -m compileall .
```

并检查节点注册、workflow JSON 可加载性、网页 generated state 以及文档与源码接口是否一致。
