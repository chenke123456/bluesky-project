# `blue_floorplan_node.py` — 平面图节点

## 作用

`BlueFloorplanNode` 根据实体位置生成快速二维平面预览。

- 节点名：`Blue 平面图节点`
- 分类：`Blue/Visualization`
- 输入：可选 `entity_pack`、可选单 `entity`、`size`
- 输出：`IMAGE`

## 数据处理

节点会合并：

- `normalize_entity_pack(entity_pack)` 后的实体列表。
- `normalize_entity(entity)` 后的单实体。

没有实体时输出带 `Empty Floorplan / No entity data provided` 的说明图。

有实体时：

1. 计算画布网格。
2. 尝试通过 `entity_position()` 读取位置。
3. 没有有效位置时使用网格 fallback。
4. 用实体稳定 ID 的 SHA-1 片段生成可重复的块颜色。
5. 绘制 `entity_type` 和 `name`。

这里的平面图是诊断/预览用途，不应被当作真实 CAD/建筑制图输出。
