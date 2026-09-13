from comfy_api.latest import io

from .blue_core import BLUE_RULE


RULE_KIND_OPTIONS = ["属性", "方法"]

PROPERTY_RULES = [
    "颜色规则",
    "二维位置规则",
    "三维位置规则",
    "大小规则",
    "布局规则",
    "绘制规则",
    "尺寸规则",
    "镜头规则",
    "材料规则",
    "强度规则",
    "刚度规则",
    "时间规则",
    "作用域规则",
    "拓扑规则",
    "载荷规则",
    "稳定性规则",
    "自定义属性规则",
]

METHOD_RULES = [
    "传导规则",
    "生长规则",
    "碰撞规则",
    "移动规则",
    "点击规则",
    "开关规则",
    "更新规则",
    "自定义方法规则",
]

RULE_NAME_OPTIONS = PROPERTY_RULES + METHOD_RULES

RULE_TYPE_MAP = {
    "颜色规则": "color",
    "二维位置规则": "position.2d",
    "三维位置规则": "position.3d",
    # 旧工作流兼容；新 UI 不再提供“位置规则”。
    "位置规则": "position",
    "大小规则": "size",
    "布局规则": "layout.controls",
    "绘制规则": "geometry.draw",
    "尺寸规则": "geometry.size",
    "镜头规则": "camera",
    "材料规则": "material",
    "强度规则": "strength",
    "刚度规则": "stiffness",
    "时间规则": "time",
    "作用域规则": "scope",
    "拓扑规则": "topology",
    "载荷规则": "load",
    "稳定性规则": "stability",
    "自定义属性规则": "custom_property",
    "传导规则": "conduction",
    "生长规则": "growth",
    "碰撞规则": "collision",
    "移动规则": "move",
    "点击规则": "click",
    "开关规则": "switch",
    "更新规则": "update",
    "自定义方法规则": "custom_method",
}

RULE_SELECTOR_COUNTS = {
    "二维位置规则": 0,
    "三维位置规则": 0,
    "大小规则": 2,
    "布局规则": 6,
    "绘制规则": 4,
    "尺寸规则": 5,
    "镜头规则": 6,
    "强度规则": 3,
    "刚度规则": 2,
    "拓扑规则": 2,
    "载荷规则": 3,
    # Unity-style movement method: mode / direction / distance / speed / space / loop.
    "移动规则": 6,
    "点击规则": 2,
    "开关规则": 2,
    "更新规则": 2,
}

MOVE_PARAM_KEYS = ("mode", "direction", "distance", "speed", "space", "loop")
CAMERA_PARAM_KEYS = ("projection", "preset", "fov", "controls", "min_distance", "max_distance")


DRAW_SHAPE_MAP = {
    "筒体": "shell",
    "封头": "head",
    "管板": "tube_sheet",
    "折流板": "baffle",
}

AXIS_MAP = {"X轴": "X", "Y轴": "Y", "Z轴": "Z"}


def _number(value, fallback=None):
    try:
        text = str(value).strip().lower().replace("米", "").replace("m", "")
        return float(text)
    except Exception:
        return fallback


def _integer(value, fallback=None):
    try:
        return int(float(str(value).strip()))
    except Exception:
        return fallback


def _compile_draw_rule(options):
    part = str(options[0] if options else "筒体")
    axis = AXIS_MAP.get(str(options[1] if len(options) > 1 else "X轴"), "X")
    detail = str(options[2] if len(options) > 2 else "")
    segments = _integer(options[3] if len(options) > 3 else 64, 64)
    shape = DRAW_SHAPE_MAP.get(part, "shell")
    params = {
        "shape": shape,
        "part_name": part,
        "axis": axis,
        "segments": max(8, segments or 64),
    }
    if shape == "shell":
        params["open_ended"] = detail != "封闭"
    elif shape == "head":
        params["side"] = "left" if detail == "左端" else "right"
        params["profile"] = "elliptical_2_1"
    elif shape == "tube_sheet":
        params["show_holes"] = detail != "不显示管孔"
    elif shape == "baffle":
        params["cut_direction"] = "bottom" if detail == "下切口" else "top"
    return params


def _compile_size_rule(options):
    part = str(options[0] if options else "筒体")
    shape = DRAW_SHAPE_MAP.get(part, "shell")
    params = {"shape": shape, "part_name": part}

    if shape == "shell":
        params.update({
            "diameter": _number(options[1] if len(options) > 1 else None, 1.6),
            "length": _number(options[2] if len(options) > 2 else None, 3.6),
            "wall_thickness": _number(options[3] if len(options) > 3 else None, 0.04),
        })
    elif shape == "head":
        params.update({
            "diameter": _number(options[1] if len(options) > 1 else None, 1.6),
            "depth": _number(options[2] if len(options) > 2 else None, 0.4),
            "thickness": _number(options[3] if len(options) > 3 else None, 0.04),
        })
    elif shape == "tube_sheet":
        params.update({
            "diameter": _number(options[1] if len(options) > 1 else None, 1.56),
            "thickness": _number(options[2] if len(options) > 2 else None, 0.16),
            "tube_count": max(1, _integer(options[3] if len(options) > 3 else None, 19) or 19),
            "tube_diameter": _number(options[4] if len(options) > 4 else None, 0.10),
        })
    elif shape == "baffle":
        params.update({
            "diameter": _number(options[1] if len(options) > 1 else None, 1.46),
            "thickness": _number(options[2] if len(options) > 2 else None, 0.08),
            "cut_ratio": _number(options[3] if len(options) > 3 else None, 0.25),
        })
    return {key: value for key, value in params.items() if value is not None}

CAMERA_PRESETS = {
    "等轴视角": {"position": {"x": 9.0, "y": 7.0, "z": 11.0}, "target": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "正视图": {"position": {"x": 0.0, "y": 0.0, "z": 12.0}, "target": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "后视图": {"position": {"x": 0.0, "y": 0.0, "z": -12.0}, "target": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "左视图": {"position": {"x": -12.0, "y": 0.0, "z": 0.0}, "target": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "右视图": {"position": {"x": 12.0, "y": 0.0, "z": 0.0}, "target": {"x": 0.0, "y": 0.0, "z": 0.0}},
    "俯视图": {"position": {"x": 0.0, "y": 12.0, "z": 0.001}, "target": {"x": 0.0, "y": 0.0, "z": 0.0}},
}

COLOR_MAP = {
    "红色": "#ef4444",
    "绿色": "#22c55e",
    "蓝色": "#3b82f6",
    "黄色": "#eab308",
    "黑色": "#111827",
    "白色": "#ffffff",
    "自定义颜色": "#ffffff",
    "白": "#ffffff",
    "极浅灰": "#f3f4f6",
    "浅灰": "#e5e7eb",
    "中灰": "#9ca3af",
    "深灰": "#4b5563",
    "黑": "#111827",
    "米白": "#fff7ed",
    "沙米": "#f5e1c6",
    "浅棕": "#e3c7a7",
    "驼色": "#c89b72",
    "棕色": "#8d5a3b",
    "深棕": "#4a2c1f",
    "浅粉": "#ffe4e6",
    "粉": "#fda4af",
    "玫红": "#fb7185",
    "红": "#ef4444",
    "深红": "#b91c1c",
    "暗红": "#7f1d1d",
    "浅黄": "#fff7d6",
    "淡黄": "#fde68a",
    "黄": "#facc15",
    "琥珀": "#f59e0b",
    "橙黄": "#d97706",
    "棕黄": "#b45309",
    "浅绿": "#ecfccb",
    "嫩绿": "#bef264",
    "黄绿": "#84cc16",
    "绿": "#22c55e",
    "深绿": "#15803d",
    "墨绿": "#052e16",
    "浅青": "#cffafe",
    "青": "#67e8f9",
    "亮青": "#22d3ee",
    "湖蓝": "#06b6d4",
    "蓝青": "#0ea5e9",
    "深青": "#0f766e",
    "浅蓝": "#dbeafe",
    "淡蓝": "#93c5fd",
    "亮蓝": "#3b82f6",
    "深蓝": "#1d4ed8",
    "海军蓝": "#1e3a8a",
    "浅紫": "#ede9fe",
    "淡紫": "#c4b5fd",
    "紫": "#8b5cf6",
    "亮紫": "#7c3aed",
    "深紫": "#5b21b6",
    "靛蓝": "#312e81",
    "浅玫": "#fce7f3",
    "粉紫": "#f9a8d4",
    "玫粉": "#ec4899",
    "洋红": "#d946ef",
    "深洋红": "#c026d3",
    "暗玫红": "#831843",
}

# “颜色规则”的下拉选项直接由 COLOR_MAP 生成。
# 以后只需要维护 COLOR_MAP，新增/删除颜色会自动同步到后端 Combo。
COLOR_OPTIONS = list(COLOR_MAP.keys())


def _normalize_color(value):
    text = str(value or "").strip()
    if text in COLOR_MAP:
        return COLOR_MAP[text]
    if text.startswith("#") and len(text) in {4, 7, 9}:
        return text.lower()
    if text.lower().startswith("rgb"):
        return text
    return COLOR_MAP["白色"]


def _color_rgb(value):
    text = _normalize_color(value)
    if not text.startswith("#"):
        return None
    raw = text[1:]
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) >= 6:
        try:
            return [int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)]
        except ValueError:
            return None
    return None

def _compile_params(rule_name, options, position_x=0.0, position_y=0.0, position_z=0.0):
    if rule_name == "二维位置规则":
        return {"vector": {"x": float(position_x), "y": float(position_y)}}
    if rule_name == "三维位置规则":
        return {"vector": {"x": float(position_x), "y": float(position_y), "z": float(position_z)}}
    if rule_name == "绘制规则":
        return _compile_draw_rule(options)
    if rule_name == "尺寸规则":
        return _compile_size_rule(options)
    if rule_name == "颜色规则":
        color = _normalize_color(options[0] if options else "")
        return {"color": color, "rgb": _color_rgb(color)}
    if rule_name == "材料规则":
        return {"material": str(options[0] if options else "自定义材料")}
    if rule_name == "强度规则":
        criterion_map = {
            "Von Mises": "von_mises",
            "Tresca": "tresca",
            "最大主应力": "max_principal",
            "许用应力": "allowable_stress",
        }
        criterion = str(options[0] if options else "Von Mises")
        safety_factor = _number(options[1] if len(options) > 1 else None, 1.5)
        allowable_raw = str(options[2] if len(options) > 2 else "自动")
        allowable = None if allowable_raw == "自动" else _number(allowable_raw, None)
        params = {
            "criterion": criterion_map.get(criterion, "von_mises"),
            "criterion_name": criterion,
            "safety_factor": safety_factor,
        }
        if allowable is not None:
            params["allowable_stress_mpa"] = allowable
        return params
    if rule_name == "刚度规则":
        model_map = {
            "线弹性": "linear_elastic",
            "轴向": "axial",
            "弯曲": "bending",
            "扭转": "torsion",
        }
        model = str(options[0] if options else "线弹性")
        limit_raw = str(options[1] if len(options) > 1 else "自动")
        limit = None if limit_raw == "自动" else _number(limit_raw, None)
        params = {
            "model": model_map.get(model, "linear_elastic"),
            "model_name": model,
        }
        if limit is not None:
            params["max_displacement_mm"] = limit
        return params
    if rule_name == "载荷规则":
        keys = ("load_type", "direction", "scope")
        return {key: value for key, value in zip(keys, options) if value not in (None, "")}
    if rule_name == "移动规则":
        params = {key: value for key, value in zip(MOVE_PARAM_KEYS, options) if value not in (None, "")}
        # 旋转仍沿用同一个 Movement 规则，但补充稳定的旋转语义，供 Three.js / Simulation 读取。
        if params.get("mode") == "旋转":
            params["rotation_axis"] = "Z轴"
            params["rotation_direction"] = params.get("direction", "顺时针")
            params["angle"] = params.get("distance", "360deg")
            params["angular_speed"] = params.get("speed", "90deg/s")
        return params
    if rule_name == "大小规则":
        keys = ("width", "height")
        return {key: value for key, value in zip(keys, options) if value not in (None, "")}
    if rule_name == "布局规则":
        mode_map = {
            "纵向排列": "column",
            "横向排列": "row",
            "网格布局": "grid",
            "左右双栏": "split",
            "左主右辅": "main_aside",
            "左辅右主": "aside_main",
            "顶部+主体": "header_main",
            "顶部+双栏": "header_split",
            "仪表盘": "dashboard",
            "自由布局": "free",
        }
        justify_map = {
            "起始": "flex-start",
            "居中": "center",
            "末尾": "flex-end",
            "两端对齐": "space-between",
            "均匀分布": "space-evenly",
        }
        align_map = {
            "拉伸": "stretch",
            "起始": "flex-start",
            "居中": "center",
            "末尾": "flex-end",
        }
        wrap_map = {"自动换行": "wrap", "不换行": "nowrap"}
        mode_name = str(options[0] if options else "纵向排列")
        justify_name = str(options[1] if len(options) > 1 else "起始")
        align_name = str(options[2] if len(options) > 2 else "拉伸")
        gap = str(options[3] if len(options) > 3 else "12px")
        wrap_name = str(options[4] if len(options) > 4 else "自动换行")
        columns_name = str(options[5] if len(options) > 5 else "自动")
        columns = None
        if columns_name != "自动":
            columns = _integer(columns_name.replace("列", ""), None)
        params = {
            "mode": mode_map.get(mode_name, "column"),
            "mode_name": mode_name,
            "justify": justify_map.get(justify_name, "flex-start"),
            "justify_name": justify_name,
            "align": align_map.get(align_name, "stretch"),
            "align_name": align_name,
            "gap": gap,
            "wrap": wrap_map.get(wrap_name, "wrap"),
            "wrap_name": wrap_name,
            "columns_name": columns_name,
        }
        if columns is not None:
            params["columns"] = max(1, min(12, columns))
        return params
    if rule_name == "镜头规则":
        raw = {key: value for key, value in zip(CAMERA_PARAM_KEYS, options) if value not in (None, "")}
        preset_name = raw.get("preset", "等轴视角")
        preset = CAMERA_PRESETS.get(preset_name, CAMERA_PRESETS["等轴视角"])
        projection = "orthographic" if raw.get("projection") == "正交" else "perspective"
        controls = raw.get("controls", "旋转+平移+缩放")
        def number(text, suffix, fallback):
            try:
                return float(str(text).replace(suffix, "").strip())
            except Exception:
                return fallback
        return {
            **raw,
            "projection": projection,
            "preset_name": preset_name,
            "position": dict(preset["position"]),
            "target": dict(preset["target"]),
            "fov": number(raw.get("fov", "45°"), "°", 45.0),
            "orbit": controls in {"旋转+平移+缩放", "旋转+缩放", "仅旋转"},
            "pan": controls in {"旋转+平移+缩放", "平移+缩放", "仅平移"},
            "zoom": controls in {"旋转+平移+缩放", "旋转+缩放", "平移+缩放", "仅缩放"},
            "min_distance": number(raw.get("min_distance", "1"), "", 1.0),
            "max_distance": number(raw.get("max_distance", "50"), "", 50.0),
            "rotate_speed": 1.0,
            "pan_speed": 1.0,
            "zoom_speed": 1.0,
        }
    return {}

RULE_OPTION_VALUES = [
    *COLOR_OPTIONS,
    # Three.js-facing drawing/size rule values. Physical dimensions use metres.
    "筒体", "封头", "管板", "折流板",
    "X轴", "Y轴", "Z轴",
    "开口", "封闭", "左端", "右端", "显示管孔", "不显示管孔", "上切口", "下切口",
    "16", "24", "32", "48", "64", "96",
    "0.01", "0.02", "0.03", "0.04", "0.05", "0.06", "0.08", "0.10", "0.12", "0.15", "0.16", "0.20", "0.25", "0.30", "0.35", "0.40", "0.42", "0.50", "0.60", "0.80",
    "1.0", "1.2", "1.4", "1.46", "1.5", "1.56", "1.6", "1.8", "2.0", "2.4", "2.8", "3.0", "3.2", "3.4", "3.6", "4.0", "4.6", "4.8", "5.0", "6.0", "8.0", "10.0",
    "7", "19", "37", "61", "91", "127",
    "透视", "正交", "等轴视角", "正视图", "后视图", "左视图", "右视图", "俯视图",
    "30°", "45°", "50°", "60°", "75°",
    "旋转+平移+缩放", "旋转+缩放", "平移+缩放", "仅旋转", "仅平移", "仅缩放", "锁定",
    "0.5", "1", "2", "5", "10", "20", "50", "100", "200",
    "自动", "25%", "50%", "75%", "100%", "120px", "180px", "240px", "320px", "480px", "640px", "720px", "960px",
    "纵向排列", "横向排列", "网格布局", "左右双栏", "左主右辅", "左辅右主",
    "顶部+主体", "顶部+双栏", "仪表盘", "自由布局",
    "起始", "居中", "末尾", "两端对齐", "均匀分布", "拉伸",
    "0px", "4px", "8px", "12px", "16px", "24px", "32px", "48px",
    "自动换行", "不换行", "1列", "2列", "3列", "4列", "6列",
    "金属", "木材", "玻璃", "塑料", "石材", "织物", "液体", "气体", "自定义材料",
    "Von Mises", "Tresca", "最大主应力", "许用应力",
    "自动", "1.0", "1.2", "1.5", "2.0", "2.5", "3.0", "100", "150", "200", "230", "250", "300", "345", "400", "500",
    "线弹性", "轴向", "弯曲", "扭转", "0.1", "0.2", "0.5", "1.0", "2.0", "5.0", "10.0",
    "始终", "白天", "夜间", "开始时", "结束时", "周期性", "自定义时间",
    "热传导", "电传导", "力传导", "流体传导", "信号传导", "禁止传导", "自定义传导",
    "停止", "缓慢", "正常", "快速", "阶段性", "定向", "自定义生长",
    "全局", "当前实体", "子级", "父级", "邻近", "局部", "自定义作用域",
    "线性", "放射状", "网格", "树状", "环状", "完全连接", "断开", "自定义拓扑",
    "允许碰撞", "禁止碰撞", "接触触发", "重叠触发", "保持间距", "自定义碰撞",
    "无载荷", "轻载", "中载", "重载", "拉伸", "压缩", "剪切", "自定义载荷",
    "稳定", "临界", "不稳定", "自动平衡", "锁定", "自定义稳定性",
    "平移", "目标位置", "往返", "轨道", "旋转", "自定义移动",
    "向左", "向右", "向上", "向下", "X正", "X负", "Y正", "Y负", "Z正", "Z负", "顺时针", "逆时针", "随机", "自定义方向",
    "10px", "25px", "50px", "100px", "200px", "400px", "45deg", "90deg", "180deg", "360deg", "自定义距离",
    "停止", "50px/s", "100px/s", "200px/s", "400px/s", "800px/s", "45deg/s", "90deg/s", "180deg/s", "360deg/s", "自定义速度",
    "本地空间", "世界空间",
    "单次", "循环", "往返循环",
    "单击", "双击", "长按", "悬停", "按下", "释放", "自定义触发",
    "无操作", "打开", "关闭", "切换", "提交", "刷新", "选择", "自定义动作",
    "开启", "关闭状态", "切换状态", "自定义开关",
    "立即", "每帧", "每秒", "事件触发", "数据变化", "自定义更新",
    "X轴", "Y轴", "Z轴", "法向", "切向", "自定义方向",
    "点", "边", "面", "实体",
    "自定义",
]


def _canonical_kind(rule_kind, rule_name):
    # 后端再次校验；即使前端动态筛选失效，也不让错误的 kind/name 组合进入下游。
    if rule_name in METHOD_RULES:
        return "method"
    if rule_name in PROPERTY_RULES:
        return "property"
    return "method" if rule_kind == "方法" else "property"


class BlueRuleNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueRuleNode",
            display_name="规则",
            category="Blue/Rules",
            inputs=[
                io.Combo.Input("rule_kind", options=RULE_KIND_OPTIONS),
                io.Combo.Input("rule_name", options=RULE_NAME_OPTIONS),
                # Use native COMBO widgets so rule selectors render as real dropdowns.
                # The browser extension narrows each dropdown to the values for the selected rule.
                io.Combo.Input("rule_option", options=RULE_OPTION_VALUES, default="白色"),
                io.Combo.Input("rule_option_2", options=RULE_OPTION_VALUES, default="白色", optional=True),
                io.Combo.Input("rule_option_3", options=RULE_OPTION_VALUES, default="白色", optional=True),
                io.Combo.Input("rule_option_4", options=RULE_OPTION_VALUES, default="白色", optional=True),
                io.Combo.Input("rule_option_5", options=RULE_OPTION_VALUES, default="白色", optional=True),
                io.Combo.Input("rule_option_6", options=RULE_OPTION_VALUES, default="白色", optional=True),
                # 位置规则使用数值矢量，不再使用离散“左/右/上/下”选项。
                io.Float.Input("position_x", default=0.0, step=0.1, optional=True),
                io.Float.Input("position_y", default=0.0, step=0.1, optional=True),
                io.Float.Input("position_z", default=0.0, step=0.1, optional=True),
            ],
            outputs=[BLUE_RULE.Output(display_name="JSON")],
        )

    @classmethod
    def execute(cls, rule_kind, rule_name, rule_option, rule_option_2=None, rule_option_3=None,
                rule_option_4=None, rule_option_5=None, rule_option_6=None,
                position_x=0.0, position_y=0.0, position_z=0.0) -> io.NodeOutput:
        kind = _canonical_kind(rule_kind, rule_name)
        selector_count = RULE_SELECTOR_COUNTS.get(rule_name, 1)
        raw_options = (rule_option, rule_option_2, rule_option_3, rule_option_4, rule_option_5, rule_option_6)[:selector_count]
        options = [value for value in raw_options if value not in (None, "")]
        if rule_name == "二维位置规则":
            options = [float(position_x), float(position_y)]
        elif rule_name == "三维位置规则":
            options = [float(position_x), float(position_y), float(position_z)]

        rule = {
            "rule_kind": kind,
            "name": rule_name,
            "rule_type": RULE_TYPE_MAP.get(rule_name, "custom"),
            "options": options,
            # Structured intermediate variables keep method semantics stable across runtimes.
            # `options` stays for compatibility with older workflows.
            "params": _compile_params(
                rule_name, options,
                position_x=position_x, position_y=position_y, position_z=position_z,
            ),
        }
        return io.NodeOutput(rule)
