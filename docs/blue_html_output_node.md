# `blue_html_output_node.py` — HTML 输出 / 实时网页节点

## 作用

`BlueHtmlOutputNode` 是 BlueNode 后端网页输出链路的入口：保存实时 JSON、按 UI stream 编译网站、写站点状态，并返回浏览器 URL。

- 节点名：`HTML 输出（插件实时网页）`
- 分类：`Blue/Output`
- 输入：`BLUE_JSON`、`title`、`filename_prefix`
- 输出：生成文件磁盘路径、live URL

默认 `filename_prefix = BlueNode/simulation`。

## 两类 stream

推荐把业务数据和 UI 描述分开：

```text
业务实体 / World / Simulation
  -> HTML 输出
  -> filename_prefix = BlueNode/data

网站实体
  -> HTML 输出
  -> filename_prefix = BlueNode/ui
```

`blue_site_state.is_ui_stream()` 判断是否属于 UI stream。UI stream 才会继续执行网站编译；普通 data stream 只写实时 JSON / meta，并返回固定 live 页面。

## 后端链路

```text
输入 JSON
  -> blue_ui_model.py
       compile_ui_model()
       build_data_context()
  -> blue_ui_compiler.py
       compile_site_html()
  -> blue_html_output_node.py
       JSON / meta / generated site / state
  -> blue_http_routes.py
       /bluenode/*
  -> html/runtime.js + runtime.css
```

### `blue_ui_model.py`

负责把 Blue Entity / World / Simulation 投影成框架无关 UI IR。关键边界是：**只让 `entity_category == 网站` 的实体进入 UI Model**。

业务实体不会因为 `entity_type` 类似 `room / machine / device` 就自动变成网页组件。

### `blue_ui_compiler.py`

把 UI Model 编译成 HTML shell。0 个有效 UI 实体时使用空站点语义，不凭空创造标题栏、卡片或占位组件。

### `blue_site_state.py`

维护 generated site 的 server-session 状态，防止 ComfyUI 重启后旧文件继续被当作当前有效页面。

### `blue_http_routes.py`

提供 live 页面、runtime JS/CSS、live data、颜色选项、clear site、generated site 等 `/bluenode/*` 接口，并在返回 generated site 前验证当前 state。

## React / Three.js 分工

网页 Runtime 只保留两个核心前端能力：

- React：DOM/UI 组件树、交互状态、页面组织。
- Three.js：3D Scene / Camera / Mesh / Material / WebGL。

当前组件 key：

```text
react.Page
react.Panel
react.Card
react.Button
react.Divider
react.Control
react.Person
react.Status
react.Decoration
react.Indicator
three.Viewer
```

输出节点根据已过滤的 UI Model 判断需要的插件：只要存在 UI 实体就启用 React；出现 `three.*` / `three.Viewer` 才启用 Three.js。结果作为 `bluenode-plugin-manifest` 写入 HTML，由 `runtime.js` 惰性加载。

输出节点**不决定** Grid、HUD、Card、Viewer 尺寸等布局；布局仍由 UI Model + Runtime 规则解释。

## 规则到 UI 的典型投影

- 颜色规则 -> appearance / UI color token / Three material color
- 二维位置规则 -> UI 平面位置
- 布局规则 -> `layout.controls`
- 大小规则 -> `layout.size`
- 材料规则 -> appearance material
- 移动/点击/开关等方法规则 -> 浏览器行为语义
- 镜头规则 -> `three.Viewer` 相机/OrbitControls

Rule 不携带任意 JavaScript；Runtime 只执行有限、结构化的行为语义。

## Three.js 数据边界

业务实体仍由 DATA_CONTEXT 提供给 `three.Viewer`。Three.js 应读取明确后端数据和规则，例如：

- `transform.position / rotation`
- `appearance.color`
- `geometry.draw / geometry.size`
- `position.3d`
- movement / camera 等规则
- executor `results.*`

不应因为网页里需要“看起来有东西”就凭空给业务实体发明位置或物理尺寸。

## 输出文件与安全

运行时 JSON 仍保存在 ComfyUI output 目录；编译后的站点文件位于插件 `web/generated/`。

输出路径处理包含两项重要保护：

1. `_safe_relative_prefix()` 清理 `.` / `..` 和非法文件名字符，防止路径穿越。
2. `_atomic_write_text()` 使用临时文件再 replace，防止浏览器轮询读到半截 JSON/HTML。

这些机制修改输出逻辑时应保留。

## 重复运行 / 站点生命周期

站点状态与 ComfyUI 前端生命周期配合，避免工作流加载时短暂断线把刚生成的网站清掉。当前设计目标包括：

- workflow load/configure 阶段不立即清站点。
- JSON 断开后延迟验证。
- 重新连接可取消 pending clear。
- 同一 stream 仍由其它连接的 HTML 输出节点持有时不清理。
- 移除节点时等待 graph replacement 稳定后再判断。

因此 generated site 不应被视为永久静态发布文件，而是当前 ComfyUI server session 的运行产物。
