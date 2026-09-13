# BlueNode 文档索引

`docs/` 按 **一个节点 Python 文件对应一份节点文档** 整理。节点文档名与源码名一致，仅扩展名由 `.py` 改为 `.md`。

这样查代码时可以直接找到同名文档，查文档时也能直接回到实现文件。原来按专题拆分的规则、Entity、Executor、UI Runtime 文档已合并到对应节点文档，避免同一行为在多份文档中重复维护。

当前节点共同组成下面这条数据链：

```text
Rule / Rule Pack
      ↓
Entity / Entity Pack / Instancer
      ↓
Computation / Executor
      ↓
World / Simulation Spec
      ↓
Render / Floorplan / HTML Output
```

以后增加机械、建筑、装修、灾害、种植等专业能力时，优先继续扩展这套现有数据流。项目整体工作流和扩展方式见 [`../README.md`](../README.md)。

## 节点文档

| Python 文件 | 文档 | ComfyUI 节点 | 分类 |
| --- | --- | --- | --- |
| `blue_rule_node.py` | [`blue_rule_node.md`](blue_rule_node.md) | 规则 | `Blue/Rules` |
| `blue_rule_pack_node.py` | [`blue_rule_pack_node.md`](blue_rule_pack_node.md) | 规则包 | `Blue/Rules` |
| `blue_entity_node.py` | [`blue_entity_node.md`](blue_entity_node.md) | 实体 | `Blue/Entities` |
| `blue_entity_instancer_node.py` | [`blue_entity_instancer_node.md`](blue_entity_instancer_node.md) | 实体实例器 | `Blue/Entities` |
| `blue_entity_pack_node.py` | [`blue_entity_pack_node.md`](blue_entity_pack_node.md) | 实体包 | `Blue/Entities` |
| `blue_executor_node.py` | [`blue_executor_node.md`](blue_executor_node.md) | 执行器 | `Blue/Executors` |
| `blue_computation_node.py` | [`blue_computation_node.md`](blue_computation_node.md) | 计算 | `Blue/Compute` |
| `blue_field_render_node.py` | [`blue_field_render_node.md`](blue_field_render_node.md) | 渲染 | `Blue/Visualization` |
| `blue_floorplan_node.py` | [`blue_floorplan_node.md`](blue_floorplan_node.md) | Blue 平面图节点 | `Blue/Visualization` |
| `blue_prompt_booster_node.py` | [`blue_prompt_booster_node.md`](blue_prompt_booster_node.md) | Blue 提示词提升器 | `Blue/AI` |
| `blue_world_node.py` | [`blue_world_node.md`](blue_world_node.md) | 世界 | `Blue/Simulation` |
| `blue_simulation_node.py` | [`blue_simulation_node.md`](blue_simulation_node.md) | 模拟 | `Blue/Simulation` |
| `blue_html_output_node.py` | [`blue_html_output_node.md`](blue_html_output_node.md) | HTML 输出（插件实时网页） | `Blue/Output` |
| `blue_json_output_test_node.py` | [`blue_json_output_test_node.md`](blue_json_output_test_node.md) | Blue JSON 输出测试 | `Blue/JSON`（未注册） |

## 推荐阅读顺序

如果第一次看项目，建议按数据流阅读：

```text
blue_rule_node
  -> blue_rule_pack_node
  -> blue_entity_node
  -> blue_entity_instancer_node / blue_entity_pack_node
  -> blue_executor_node / blue_computation_node
  -> blue_world_node
  -> blue_simulation_node
  -> blue_field_render_node / blue_floorplan_node
  -> blue_html_output_node
```

开发扩展约定集中在 [`DEVELOPMENT.md`](DEVELOPMENT.md)。

## 非节点 Python 模块

这些文件不是 ComfyUI 节点，因此不再各自拆成节点文档；它们在使用它们的节点文档中说明：

- `__init__.py`：扩展入口、节点注册、`WEB_DIRECTORY`、HTTP 路由导入。
- `blue_core.py`：Blue 类型、JSON 兼容、规则/实体规范化、稳定 ID、评分和图片辅助函数。
- `executors/`：专业执行器注册、规则读取、设备选择、强度/刚度分析程序；集中见 [`blue_executor_node.md`](blue_executor_node.md)。
- `blue_ui_model.py`、`blue_ui_compiler.py`、`blue_site_state.py`、`blue_http_routes.py`：网页 UI 投影、HTML 编译、生成站点状态和 HTTP 路由；集中见 [`blue_html_output_node.md`](blue_html_output_node.md)。
- `html/runtime.js`、`html/runtime.css`：浏览器端 React / Three.js Runtime。
- `web/js/`：ComfyUI 编辑器内的节点交互增强。

## 原专题文档迁移位置

旧 `docs/` 的内容没有继续按专题平铺，而是合并到以下节点文档：

- 颜色、二维/三维位置、大小、布局、绘制、尺寸、镜头、属性/方法、移动规则 → [`blue_rule_node.md`](blue_rule_node.md)
- 实体/系统概念、网站实体边界、机械/化工设备语义 → [`blue_entity_node.md`](blue_entity_node.md)
- 实体实例化 → [`blue_entity_instancer_node.md`](blue_entity_instancer_node.md)
- Executor 架构、Device、强度/刚度扩展 → [`blue_executor_node.md`](blue_executor_node.md)
- UI Runtime、React/Three.js、网站生成、重复运行生命周期 → [`blue_html_output_node.md`](blue_html_output_node.md)
- Simulation Web 数据流 → [`blue_world_node.md`](blue_world_node.md)、[`blue_simulation_node.md`](blue_simulation_node.md)、[`blue_html_output_node.md`](blue_html_output_node.md)
