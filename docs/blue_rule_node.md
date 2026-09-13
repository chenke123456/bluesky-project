# `blue_rule_node.py` — 规则节点

## 作用

`BlueRuleNode` 是 BlueNode 规则体系的统一输入端。节点先选择 **属性 / 方法**，再选择具体规则，把 UI 输入编译为稳定的 `BLUE_RULE` JSON。

- 节点名：`规则`
- 分类：`Blue/Rules`
- 输出：`BLUE_RULE`
- 源码：`blue_rule_node.py`

规则本身只表达语义，不直接执行 Three.js、React、Simulation 或 Executor。不同下游按 `rule_type` / `params` 解释同一份规则数据。

## 输出结构

```json
{
  "rule_kind": "property",
  "name": "颜色规则",
  "rule_type": "color",
  "options": ["红色"],
  "params": {
    "color": "#ef4444",
    "rgb": [239, 68, 68]
  }
}
```

字段含义：

- `rule_kind`：规范化后的 `property` 或 `method`。
- `name`：中文规则名。
- `rule_type`：供程序消费的稳定类型名。
- `options`：保留 UI 原始选项，兼容旧工作流。
- `params`：结构化中间参数，优先供新 Runtime / Executor 使用。

后端会通过 `_canonical_kind()` 再次校验规则名属于属性还是方法，即使前端动态下拉失效，也不会把已知方法规则误标为属性规则。

## 属性规则

当前属性规则包括：颜色、二维位置、三维位置、大小、布局、绘制、尺寸、镜头、材料、强度、刚度、时间、作用域、拓扑、载荷、稳定性和自定义属性。

### 颜色规则

`rule_type = color`。颜色下拉由 `COLOR_MAP` 生成；后端把颜色统一写入：

```json
{
  "params": {
    "color": "#3b82f6",
    "rgb": [59, 130, 246]
  }
}
```

`BlueWorldNode` 会把实体最终生效的颜色规则落到 `appearance.color`。同类规则遵循后写覆盖前写的语义。

### 二维位置规则

`rule_type = position.2d`，使用 `position_x / position_y` 数值输入：

```json
{
  "params": {
    "vector": {"x": 100.0, "y": 50.0}
  }
}
```

主要用于网站 UI 平面偏移，通常按像素语义解释。

### 三维位置规则

`rule_type = position.3d`，使用 `position_x / position_y / position_z`：

```json
{
  "params": {
    "vector": {"x": 1.0, "y": 2.0, "z": 3.0}
  }
}
```

Three.js Selector 应直接读取该向量，不根据实体名称推断位置。

### 大小规则

`rule_type = size`，结构化为：

```json
{
  "params": {
    "width": "480px",
    "height": "320px"
  }
}
```

主要供网站实体的 CSS 尺寸使用；普通业务实体不会因为存在大小规则就自动成为 UI。

### 布局规则

`rule_type = layout.controls`，用于网站容器内控件的 Flex/Grid 等布局，不参与 Three.js 几何建模。

```json
{
  "params": {
    "mode": "header_split",
    "justify": "flex-start",
    "align": "stretch",
    "gap": "16px",
    "wrap": "wrap",
    "columns": 2
  }
}
```

当前布局模式映射：

| UI 选项 | `params.mode` |
| --- | --- |
| 纵向排列 | `column` |
| 横向排列 | `row` |
| 网格布局 | `grid` |
| 左右双栏 | `split` |
| 左主右辅 | `main_aside` |
| 左辅右主 | `aside_main` |
| 顶部+主体 | `header_main` |
| 顶部+双栏 | `header_split` |
| 仪表盘 | `dashboard` |
| 自由布局 | `free` |

### 绘制规则

`rule_type = geometry.draw`。它决定 Three.js 应绘制什么几何，而不是由实体名称自动补几何。

| UI 对象 | `params.shape` |
| --- | --- |
| 筒体 | `shell` |
| 封头 | `head` |
| 管板 | `tube_sheet` |
| 折流板 | `baffle` |

同时会编译轴向、分段数和对应几何细节，如封头左右端、管板是否显示管孔、折流板切口方向等。

### 尺寸规则

`rule_type = geometry.size`，物理尺寸按米处理。

- 筒体：直径、长度、壁厚。
- 封头：直径、深度、厚度。
- 管板：直径、厚度、管孔数量、管孔直径。
- 折流板：直径、厚度、切口率。

Three.js 三维几何应以 `geometry.draw + geometry.size` 为权威规则；实体选择本身不应偷偷补齐绘制类型或尺寸。

### 镜头规则

`rule_type = camera`，建议挂在 `网站 -> 3D视图` 实体上。参数包括：

- 投影：透视 / 正交。
- 预设：等轴、正、后、左、右、俯视。
- FOV。
- OrbitControls 能力：旋转、平移、缩放及锁定组合。
- 最小/最大距离。

编译后会得到 `projection`、`position`、`target`、`fov`、`orbit`、`pan`、`zoom` 等稳定字段。镜头只改变观察状态，不修改业务实体的 transform 或尺寸。

### 强度 / 刚度规则

强度规则会编译准则、安全系数和可选许用应力；刚度规则会编译模型和可选最大位移限制。它们主要由 `executors/` 中的专业执行器读取。

## 方法规则

当前方法规则包括：传导、生长、碰撞、移动、点击、开关、更新和自定义方法。

### 移动规则

`rule_type = move`，采用稳定的 Unity-style 中间模型：

```json
{
  "params": {
    "mode": "平移",
    "direction": "向右",
    "distance": "100px",
    "speed": "200px/s",
    "space": "本地空间",
    "loop": "往返循环"
  }
}
```

字段语义：

- `mode`：平移、目标位置、往返、轨道、旋转、自定义移动。
- `direction`：常用二维方向、XYZ 方向或旋转方向。
- `distance`：位移或旋转角度。
- `speed`：线速度或角速度。
- `space`：本地空间 / 世界空间。
- `loop`：单次 / 循环 / 往返循环。

当 `mode = 旋转` 时，后端额外补充 `rotation_axis / rotation_direction / angle / angular_speed`。

网站实体可由浏览器 Runtime 执行这些方法语义；非网站实体只携带方法数据，是否运动由 World / Simulation / Renderer 的后续实现决定。

## 规则消费边界

```text
BlueRuleNode
  -> BlueRulePackNode / BlueEntityNode
  -> World / Executor / UI Model
  -> 浏览器 Runtime / Three.js / 专业分析程序
```

核心原则：规则节点负责“编译规则”，不负责“执行规则”。
