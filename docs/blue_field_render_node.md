# `blue_field_render_node.py` — 字段渲染节点

## 作用

`BlueFieldRenderNode` 把 `BLUE_FIELD` / 兼容 JSON 快速渲染成 ComfyUI `IMAGE`，用于查看计算结果摘要。

- 节点名：`渲染`
- 分类：`Blue/Visualization`
- 输入：可选 `JSON`、`render_mode`、`palette`、`resolution`
- 输出：`IMAGE`

参数：

- `render_mode`：`heatmap / arrows / both`
- `palette`：字符串，默认 `blue`
- `resolution`：128–2048，默认 512

## 当前实现边界

当前版本主要创建一张深色 Pillow 图像并绘制 `speed / coverage / palette` 文本摘要。`render_mode` 目前存在于 schema，但执行代码尚未根据它真正绘制热力图或箭头。

输入如果没有 `speed`，会回退读取 `intensity`；`coverage` 默认 0.5。

该节点是 ComfyUI 图片预览，不是网页 UI / Three.js Renderer。
