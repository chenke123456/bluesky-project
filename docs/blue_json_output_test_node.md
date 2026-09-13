# `blue_json_output_test_node.py` — JSON 调试节点

## 作用

`BlueJsonOutputTestNode` 用于把文本 JSON 解析成 `BLUE_JSON`，并同时输出格式化显示文本。

- 节点名：`Blue JSON 输出测试`
- 分类：`Blue/JSON`
- 输入：多行 `json_text`
- 输出：`BLUE_JSON` + 格式化字符串

实现使用：

- `maybe_json()`：尝试解析输入。
- `pretty_json()`：对 dict/list 做缩进格式化。

## 注册状态

当前 `__init__.py` **没有**把该类加入 `BlueNodeExtension.get_node_list()`，所以默认不会出现在 ComfyUI 节点菜单中。它属于开发/调试辅助文件。
