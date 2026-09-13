# `blue_entity_node.py` — 实体节点

## 作用

`BlueEntityNode` 描述“对象是什么”，并把连接进来的规则挂到对象上。它不负责运行规则，也不应因为实体名称自动生成 Three.js 绘图规则。

- 节点名：`实体`
- 分类：`Blue/Entities`
- 输出：`BLUE_ENTITY`
- 输入：基础规则 `JSON`、实体种类、实体对象，以及可选的绘图规则/尺寸规则。

## 两级实体语义

实体使用：

```text
entity_category -> entity_item
```

当前大类包括设备、家具、网站、系统、机械部件、化工设备、电子元件、木工对象、建筑、人物、自然、3D 对象和自定义。

后端会再次校验 `entity_item` 是否属于所选 `entity_category`。因此即使 ComfyUI 前端的动态下拉未加载，错误组合也会被纠正。

## 输出结构

典型输出：

```json
{
  "name": "machine",
  "entity_type": "machine",
  "entity_category": "机械部件",
  "entity_item": "齿轮",
  "entity_name": "齿轮",
  "properties": [],
  "methods": [],
  "rules": []
}
```

- `entity_category / entity_item` 是当前明确的业务分类。
- `entity_type` 主要保留给旧业务数据、Simulation 和渲染兼容。
- `properties / methods` 是面向对象式规则分组。
- `rules` 保留扁平兼容列表。

## 规则连接

实体可以从 `JSON` 输入读取已有规则，同时接收独立的 `绘图规则` 和 `尺寸规则` 输入。最终统一写入 `entity.rules`。

重要边界：实体节点**不会**因为你选择了“封头”“筒体”等条目就自动生成 `geometry.draw` / `geometry.size`。需要程序化三维几何时，应显式连接 `绘制规则 + 尺寸规则`。

## 网站实体边界

只有：

```text
entity_category == "网站"
```

的实体会直接进入网页 UI 编译。其他类别是业务数据，不会因为 `entity_type` 恰好等于 `room / machine / device` 就自动生成 React 组件。

网站 item 的当前投影语义：

| 网站 item | UI Component |
| --- | --- |
| 页面 | `react.Page` |
| 面板 | `react.Panel` |
| 按钮 | `react.Button` |
| 分隔线 | `react.Divider` |
| 控件 | `react.Control` |
| 卡片 | `react.Card` |
| 人物信息 | `react.Person` |
| 状态 | `react.Status` |
| 指示器 | `react.Indicator` |
| 装饰 | `react.Decoration` |
| 3D视图 | `three.Viewer` |

普通机械、建筑、设备等实体仍然可通过 `DATA_CONTEXT` 被网站实体读取，或由 `网站 -> 3D视图` 消费。

## “系统”与“具体对象”

BlueNode 把系统和对象分开：

- 系统：机械系统、电子系统、控制系统、时间系统等运行机制。
- 对象：法兰、齿轮、电阻、木板等被规则作用的具体实体。

系统本身仍然采用实体模型，因此也可以挂属性规则和方法规则，但不会把“法兰”自动归类成“机械系统”。

## 机械 / 化工设备

机械部件和化工设备保留 `entity_item` / `entity_category` 供浏览器 Renderer 识别。化工设备还可以携带后端定义的 `geometry` 数据。

当前化工设备包括压力容器、储罐、罐子、冷凝器、再沸器，以及可独立选择的封头、筒体、折流板、管板、列管。

职责边界：

```text
Entity：对象身份；部分设备的固有 geometry 数据
Rule：显式绘图/尺寸/位置/颜色/行为语义
World：组织实体、补运行状态，不发明业务尺寸
Renderer：读取业务数据与规则做可视化
```
