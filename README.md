# Blue

Blue 是一个基于 **ComfyUI 节点**构建的蓝图、计算与模拟原型。

当前仓库 `bn_camera_rule` 把一个方案拆成可以连接和复用的 **规则、实体、计算、Executor、World、Simulation、可视化与网页输出**。用户可以通过节点组合方案，修改其中一部分后重新计算、重新模拟和重新比较，而不需要每次从头生成整个结果。

这套结构也为后续接入机械、建筑、装修、灾害、风水、种植、人体、菜肴等专业模块保留统一入口：专业能力继续使用现有的 Rule、Entity、Executor、World 和 Simulation 数据链路，而不是各自建立互不兼容的系统。

```text
Rule / Rule Pack
      ↓
Entity / Instancer / Entity Pack
      ↓
Computation / Executor
      ↓
World / Simulation Spec
      ↓
Render / Floorplan / HTML Output
```

当前版本首先把这套通用骨架跑通，再在同一结构上继续增加专业规则、专业计算、仿真和评估能力。

---

## 1. 当前支持的能力

当前 `bn_camera_rule` 是一套可运行的 ComfyUI 自定义节点实现，主要提供：

- **规则建模**：创建属性规则、方法规则，并组合为规则包。
- **实体建模**：创建实体、批量实例化实体、组合实体包。
- **计算节点**：对实体及其规则做基础关系 / 场计算。
- **统一执行器**：以 `JSON -> Executor -> JSON` 接口执行专业分析。
- **强度 / 刚度分析**：当前 `executors/` 已注册两类专业计算程序。
- **世界表示**：把实体和规则编译为统一 World 数据。
- **模拟规格**：基于 World 生成 Simulation Spec。
- **图像可视化**：生成字段渲染图和平面图。
- **AI 辅助入口**：把 Blue JSON 与模式 / Schema 提示组合成可继续交给模型的提示词。
- **网页 UI 输出**：把 Blue JSON 编译为 UI Model，并输出实时网页。
- **ComfyUI HTTP 路由**：提供实时页面、数据和运行时资源访问接口。

这些能力不是彼此独立的工具，而是同一条蓝图数据链上的积木。后续增加专业模块时，可以继续向现有实体写入专业数据、向规则包增加约束、通过 Executor 运行专业程序，并把结果带入 World、Simulation 和输出节点。

---

## 2. 当前节点

当前插件注册 13 个主要节点。

| ComfyUI 分类 | 节点 | Python 文件 | 作用 |
| --- | --- | --- | --- |
| `Blue/Rules` | 规则 | `blue_rule_node.py` | 创建单条属性 / 方法规则 |
| `Blue/Rules` | 规则包 | `blue_rule_pack_node.py` | 组合多条规则 |
| `Blue/Executors` | 执行器 | `blue_executor_node.py` | 调用专业计算程序并写回结果 |
| `Blue/Entities` | 实体 | `blue_entity_node.py` | 创建蓝图中的对象 |
| `Blue/Entities` | 实体实例器 | `blue_entity_instancer_node.py` | 批量生成和布置对象 |
| `Blue/Entities` | 实体包 | `blue_entity_pack_node.py` | 组合多个对象 |
| `Blue/AI` | Blue 提示词提升器 | `blue_prompt_booster_node.py` | 将 Blue JSON 组织为 AI 可继续处理的提示输入 |
| `Blue/Compute` | 计算 | `blue_computation_node.py` | 关系 / 字段计算 |
| `Blue/Visualization` | 渲染 | `blue_field_render_node.py` | 字段结果预览 |
| `Blue/Visualization` | Blue 平面图节点 | `blue_floorplan_node.py` | 空间和平面预览 |
| `Blue/Output` | HTML 输出（插件实时网页） | `blue_html_output_node.py` | 交互式网页输出 |
| `Blue/Simulation` | 世界 | `blue_world_node.py` | 把实体与规则整理为统一 World |
| `Blue/Simulation` | 模拟 | `blue_simulation_node.py` | 生成 Simulation Spec |

另有 `blue_json_output_test_node.py` 用于 JSON 输出测试，目前未注册为主要节点。

每个节点的详细输入、输出、数据格式和职责见 [`docs/README.md`](docs/README.md)。

---

## 3. 现有节点如何组成方案

### 3.1 规则 + 实体

规则节点负责描述对象需要携带或遵守的数据与行为约束，实体节点负责描述方案中的对象。规则可以单独创建，也可以先组合成规则包后交给实体或后续计算链使用。

```text
规则 ──> 规则包 ──┐
                  ├──> 实体 ──> 实体包
实体基础参数 ─────┘
```

以后新增尺寸、材料、结构、空间、环境或其他专业规则时，优先继续扩展这条现有 Rule / Rule Pack 链路，让不同专业模块可以读取相同的规则数据。

### 3.2 实体 + 专业 Executor

```text
规则 / 规则包 ----┐
                  ├-> 实体 / 实体包 -> 执行器 -> JSON
实体专业参数 ------┘
```

当前 Executor 已支持：

- 强度分析
- 刚度分析

执行器保留原始业务 JSON，并把自己的结果写入 `results` 命名空间。这样多个专业程序可以依次增加结果，而不用把前一个步骤的数据覆盖掉。

机械、建筑、装修、灾害、种植等后续专业能力也可以沿用同一模式：由实体描述对象，由规则提供条件，由不同 Executor 执行具体专业计算。

### 3.3 World + Simulation Spec

```text
实体包 ----┐
           ├-> 世界 -> 模拟 -> BLUE_SIMULATION_SPEC
规则包 ----┘
```

`世界` 节点把当前方案中的实体和规则整理成统一 World；`模拟` 节点描述这个 World 应该如何被推演。

当前 `模拟` 节点只生成配置说明，包括 `tick_rate` 与启用的系统列表；它不会启动线程、会话、 tick loop 或真实运动。以后增加真实仿真时，可以继续以 World 和 Simulation Spec 作为边界扩展运行时，而不需要推翻现有节点数据结构。

### 3.4 计算与可视化

`计算` 节点可以对实体和规则进行基础关系 / 字段计算，结果可以继续送到字段渲染和平面图节点进行查看。

```text
实体 / 规则
    -> 计算
    -> 字段数据 / 关系结果
    -> 渲染 / 平面图
```

这使方案不仅可以保存结构，还可以经过计算后得到可比较的结果表达。

### 3.5 Blue JSON -> 实时网页

```text
Blue JSON
   -> blue_ui_model.compile_ui_model()
   -> blue_ui_compiler.compile_site_html()
   -> HTML 输出节点
   -> /bluenode/* HTTP 路由
   -> html/runtime.js + html/runtime.css
```

网页 UI 只从明确标记为网站类型的实体中编译 UI 投影，避免把普通机械 / 建筑实体误当作界面组件。

### 3.6 AI 接入现有数据链

`Blue 提示词提升器` 当前负责把 Blue JSON、模式和 Schema 信息整理为可以继续交给模型的输入。

后续如果增加“从目标生成多个候选方案”的能力，生成结果也应落回现有的 Rule、Entity、Executor、World、Simulation 数据结构，再继续计算和比较。这样 AI 生成的方案和用户手工拼装的方案使用同一套节点链路。

---

## 4. 在 ComfyUI 中安装与运行

将本目录放到 ComfyUI 的自定义节点目录：

```text
ComfyUI/
└── custom_nodes/
    └── bn_camera_rule/
        ├── __init__.py
        ├── blue_core.py
        ├── blue_entity_node.py
        └── ...
```

然后重启 ComfyUI。

本项目使用 ComfyUI 新版扩展入口：

```python
async def comfy_entrypoint() -> BlueNodeExtension:
    return BlueNodeExtension()
```

入口位于 [`__init__.py`](__init__.py)，插件前端目录通过：

```python
WEB_DIRECTORY = "./web"
```

暴露给 ComfyUI。

### 运行依赖

代码直接依赖或使用：

- ComfyUI / `comfy_api.latest`
- Python 3
- `numpy`
- `torch`
- `Pillow`
- `aiohttp`（由 ComfyUI 服务端环境提供）

如果 ComfyUI 环境已经包含这些库，通常无需额外安装独立依赖文件。

---

## 5. 数据与扩展方式

Blue 的现有数据结构就是以后继续增加专业能力的基础。

### 实体

实体用于描述方案里的对象。不同专业模块可以增加自己的类别、参数和几何信息，但应尽量保持稳定 ID 和统一的实体包装方式，这样一个对象可以继续被规则、Executor、World、Simulation 和输出节点引用。

### 规则

规则通过 `规则` 与 `规则包` 节点创建和组合。新增专业约束时，应优先扩展现有规则类型和下游读取逻辑，而不是另外建立一套不兼容的约束系统。

### Executor

专业计算统一通过 Executor 接口扩展：

```python
def execute(JSON, *, device):
    ...
```

新的专业 Executor 应尽量保留输入业务 JSON，并把自己的结果写到独立 `results.<namespace>` 下。这样同一套方案可以连续经过多个专业分析步骤，也方便比较不同方案的多维结果。

### World 与 Simulation

World 表达一个方案在某个阶段的统一状态；Simulation Spec 表达这个世界应该如何被推演。以后增加真实时间步、环境变化、对象行为或更复杂系统时，优先沿着这两个边界扩展。

### 输出与比较

字段渲染、平面图和 HTML 输出负责把结构或计算结果展示出来。后续增加成本、安全、舒适度、生态、施工性等评估时，也应尽量保留各维度结果，让用户可以比较、替换方案中的一部分，再重新运行后续节点，而不是只得到一个不可解释的总分。

---

## 6. 当前边界与后续扩展

当前仓库已经完成的是 **通用节点骨架和部分专业 Executor**，还不是完整的城市级模拟系统。

后续能力可以直接沿现有结构逐步加入：

```text
现有 Rule / Entity 数据结构
        ↓
增加专业规则与专业实体参数
        ↓
增加机械 / 建筑 / 装修 / 灾害 / 种植等 Executor
        ↓
增加更完整的 World / Simulation 运行能力
        ↓
增加成本 / 安全 / 舒适度 / 生态等评估结果
        ↓
让 AI 或用户生成多套方案并重复运行同一条链路
        ↓
组合为更大尺度的社区与城市方案
```

也就是说，后续功能不是在当前程序旁边再做一套“未来系统”，而是继续往现有节点、数据结构和 Executor 体系里增加能力。

---

## 7. 项目目录

```text
bn_camera_rule/
├── README.md                            # 项目介绍、当前能力、工作流与扩展方式
├── __init__.py                          # ComfyUI 扩展入口与节点注册
├── blue_core.py                         # Blue 数据类型与公共函数
├── blue_*_node.py                       # 节点实现
├── executors/                           # 专业 Executor
├── html/                                # 实时网页 Runtime
├── web/                                 # ComfyUI 前端与 generated 状态
├── workflows/                           # 示例工作流
└── docs/
    ├── README.md                        # 节点文档索引
    ├── DEVELOPMENT.md                   # 开发与文档约定
    └── blue_*_node.md                   # 每个节点 .py 对应一份文档
```

如果想了解项目怎么组合，先读本 README；如果要查看某个节点的具体输入、输出和实现行为，再进入 [`docs/README.md`](docs/README.md)。
