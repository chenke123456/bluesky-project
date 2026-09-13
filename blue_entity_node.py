from copy import deepcopy

from comfy_api.latest import io

from .blue_core import BLUE_ENTITY, BLUE_RULE, collect_rules, maybe_json


# 实体节点只负责描述“是什么”。
# 第一层选择大类，第二层选择该类中的具体对象。
ENTITY_CATEGORIES = [
    "设备",
    "家具",
    "网站",
    "系统",
    "机械部件",
    "化工设备",
    "电子元件",
    "木工对象",
    "建筑",
    "人物",
    "自然",
    "3D对象",
    "自定义",
]

ENTITY_ITEMS = {
    "设备": [
        "风扇", "空调", "灯", "摄像头", "传感器", "开关", "显示器", "音箱",
        "路由器", "服务器", "电机", "水泵", "发电机", "机器人", "车辆", "通用设备",
    ],
    "家具": [
        "桌子", "椅子", "沙发", "床", "柜子", "书架", "茶几", "餐桌",
        "工作台", "灯具", "装饰物", "通用家具",
    ],
    "网站": [
        "页面", "面板", "按钮", "分隔线", "控件", "卡片", "人物信息",
        "状态", "指示器", "装饰", "3D视图",
    ],
    # “系统”表示一套可挂载属性/方法规则的运行机制。系统与具体零部件是不同概念。
    "系统": [
        "机械系统", "电子系统", "木工系统", "液压系统", "气动系统",
        "电力系统", "控制系统", "通信系统", "时间系统", "天气系统",
        "环境系统", "交通系统", "经济系统", "阴阳系统", "五行系统",
        "河图洛书系统", "自定义系统",
    ],
    # 具体对象独立于“系统”；例如法兰是机械部件，不是机械系统。
    "机械部件": [
        "法兰", "齿轮", "轴", "轴承", "联轴器", "皮带轮", "链轮",
        "弹簧", "凸轮", "丝杠", "导轨", "紧固件", "通用机械部件",
    ],
    # 化工设备的几何定义属于实体本身；World 只组织实体，不负责给设备设尺寸。
    "化工设备": [
        "压力容器", "储罐", "罐子", "冷凝器", "再沸器",
        "封头", "筒体", "折流板", "管板", "列管",
        "通用化工设备",
    ],
    "电子元件": [
        "电阻", "电容", "电感", "二极管", "三极管", "MOS管", "继电器",
        "芯片", "传感器元件", "连接器", "电路板", "通用电子元件",
    ],
    "木工对象": [
        "木板", "木方", "榫头", "榫眼", "柜体", "门板", "抽屉",
        "层板", "木框", "木工连接件", "通用木工对象",
    ],
    "建筑": [
        "房屋", "房间", "门", "墙", "住宅", "办公楼", "商业建筑", "工厂",
        "仓库", "学校", "医院", "道路", "桥梁", "通用建筑",
    ],
    "人物": [
        "市民", "工人", "学生", "医生", "教师", "顾客", "游客", "驾驶员", "通用人物",
    ],
    "自然": [
        "树木", "花草", "动物", "微生物", "天气", "水体", "山体", "通用自然对象",
    ],
    "3D对象": [
        "3D场景", "3D模型", "机械模型", "建筑模型", "车辆模型", "地形", "通用3D对象",
    ],
    "自定义": ["自定义实体"],
}

# Combo 的初始全集。前端扩展会根据“种类”动态缩小第二个下拉框；
# 即使前端扩展没有加载，后端仍会校验并纠正 category/item 组合。
ALL_ENTITY_ITEMS = []
for _category in ENTITY_CATEGORIES:
    for _item in ENTITY_ITEMS[_category]:
        if _item not in ALL_ENTITY_ITEMS:
            ALL_ENTITY_ITEMS.append(_item)


# entity_type 只保留为业务/世界数据的兼容类型。
# UI 是否显示不再由 entity_type 决定：只有 entity_category == "网站" 才会进入 UI Compiler。
ITEM_ENTITY_TYPE = {
    # 设备
    "风扇": "fan",
    "空调": "device",
    "灯": "device",
    "摄像头": "device",
    "传感器": "device",
    "开关": "device",
    "显示器": "device",
    "音箱": "device",
    "路由器": "device",
    "服务器": "machine",
    "电机": "machine",
    "水泵": "machine",
    "发电机": "machine",
    "机器人": "machine",
    "车辆": "machine",
    "通用设备": "device",

    # 家具
    "桌子": "furniture",
    "椅子": "furniture",
    "沙发": "furniture",
    "床": "furniture",
    "柜子": "furniture",
    "书架": "furniture",
    "茶几": "furniture",
    "餐桌": "furniture",
    "工作台": "furniture",
    "灯具": "furniture",
    "装饰物": "furniture",
    "通用家具": "furniture",

    # 网站：entity_item 决定对应的网站组件；UI Compiler 只处理这一大类
    "页面": "house",          # react.Page
    "面板": "room",           # react.Panel
    "按钮": "door",           # react.Button
    "分隔线": "wall",         # react.Divider
    "控件": "device",         # react.Control
    "卡片": "furniture",      # react.Card
    "人物信息": "human",      # react.Person
    "状态": "weather",        # react.Status
    "指示器": "fan_part",     # react.Indicator
    "装饰": "plant",          # react.Decoration
    "3D视图": "machine",      # three.Viewer


    # 系统：系统本身也是实体，因此同样可以挂载属性规则和方法规则；
    # 但不会因为名称中含“机械/电子/木工”就被当成对应的具体零部件。
    "机械系统": "custom",
    "电子系统": "custom",
    "木工系统": "custom",
    "液压系统": "custom",
    "气动系统": "custom",
    "电力系统": "custom",
    "控制系统": "custom",
    "通信系统": "custom",
    "时间系统": "custom",
    "天气系统": "custom",
    "环境系统": "custom",
    "交通系统": "custom",
    "经济系统": "custom",
    "阴阳系统": "custom",
    "五行系统": "custom",
    "河图洛书系统": "custom",
    "自定义系统": "custom",

    # 机械部件
    "法兰": "machine",
    "齿轮": "machine",
    "轴": "machine",
    "轴承": "machine",
    "联轴器": "machine",
    "皮带轮": "machine",
    "链轮": "machine",
    "弹簧": "machine",
    "凸轮": "machine",
    "丝杠": "machine",
    "导轨": "machine",
    "紧固件": "machine",
    "通用机械部件": "machine",

    # 化工设备。保持 machine 业务类型以兼容现有 Simulation；渲染器通过
    # entity_category/entity_item/geometry.kind 识别具体设备。
    "压力容器": "machine",
    "储罐": "machine",
    "罐子": "machine",
    "冷凝器": "machine",
    "再沸器": "machine",
    "封头": "machine",
    "筒体": "machine",
    "折流板": "machine",
    "管板": "machine",
    "列管": "machine",
    "通用化工设备": "machine",

    # 电子元件
    "电阻": "device",
    "电容": "device",
    "电感": "device",
    "二极管": "device",
    "三极管": "device",
    "MOS管": "device",
    "继电器": "device",
    "芯片": "device",
    "传感器元件": "device",
    "连接器": "device",
    "电路板": "device",
    "通用电子元件": "device",

    # 木工对象
    "木板": "custom",
    "木方": "custom",
    "榫头": "custom",
    "榫眼": "custom",
    "柜体": "furniture",
    "门板": "custom",
    "抽屉": "furniture",
    "层板": "custom",
    "木框": "custom",
    "木工连接件": "custom",
    "通用木工对象": "custom",

    # 建筑
    "房屋": "house",
    "房间": "room",
    "门": "door",
    "墙": "wall",
    "住宅": "house",
    "办公楼": "house",
    "商业建筑": "house",
    "工厂": "house",
    "仓库": "house",
    "学校": "house",
    "医院": "house",
    "道路": "custom",
    "桥梁": "custom",
    "通用建筑": "house",

    # 人物
    "市民": "human",
    "工人": "human",
    "学生": "human",
    "医生": "human",
    "教师": "human",
    "顾客": "human",
    "游客": "human",
    "驾驶员": "human",
    "通用人物": "human",

    # 自然
    "树木": "plant",
    "花草": "plant",
    "动物": "animal",
    "微生物": "microbe",
    "天气": "weather",
    "水体": "custom",
    "山体": "custom",
    "通用自然对象": "custom",

    # 3D
    "3D场景": "machine",
    "3D模型": "machine",
    "机械模型": "machine",
    "建筑模型": "machine",
    "车辆模型": "machine",
    "地形": "machine",
    "通用3D对象": "machine",

    "自定义实体": "custom",
}


# 化工设备的“设计几何”由实体定义持有，而不是由 World 推断。
# 这些是可直接渲染的初始实体参数；以后可以再用专用几何规则覆盖。
PROCESS_EQUIPMENT_GEOMETRY = {
    "压力容器": {
        "kind": "pressure_vessel",
        "orientation": "vertical",
        "diameter": 1.8,
        "height": 4.0,
        "head": "elliptical",
        "support": "legs",
    },
    "储罐": {
        "kind": "tank",
        "orientation": "vertical",
        "diameter": 3.2,
        "height": 3.4,
        "roof": "cone",
    },
    "罐子": {
        "kind": "tank",
        "orientation": "vertical",
        "diameter": 2.4,
        "height": 2.8,
        "roof": "cone",
    },
    "冷凝器": {
        "kind": "condenser",
        "orientation": "horizontal",
        "length": 4.8,
        "diameter": 1.6,
        "support": "saddles",
    },
    "再沸器": {
        "kind": "reboiler",
        "orientation": "horizontal",
        "length": 4.6,
        "diameter": 1.9,
        "support": "saddles",
    },
    "封头": {
        "kind": "vessel_head",
        "orientation": "horizontal",
        "diameter": 1.6,
        "depth": 0.42,
        "head": "elliptical_2_1",
        "side": "right",
    },
    "筒体": {
        "kind": "shell_section",
        "orientation": "horizontal",
        "length": 3.6,
        "diameter": 1.6,
        "open_ended": True,
    },
    "折流板": {
        "kind": "baffle",
        "orientation": "transverse",
        "diameter": 1.46,
        "thickness": 0.08,
        "cut_ratio": 0.25,
    },
    "管板": {
        "kind": "tube_sheet",
        "orientation": "transverse",
        "diameter": 1.56,
        "thickness": 0.16,
        "tube_count": 19,
        "tube_diameter": 0.10,
    },
    "列管": {
        "kind": "heat_exchange_tube",
        "orientation": "horizontal",
        "length": 3.8,
        "diameter": 0.08,
        "wall": 0.008,
    },
    "通用化工设备": {
        "kind": "process_equipment",
        "orientation": "vertical",
        "diameter": 1.8,
        "height": 2.8,
    },
}


class BlueEntityNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueEntityNode",
            display_name="实体",
            category="Blue/Entities",
            inputs=[
                BLUE_RULE.Input("JSON", optional=True),
                io.Combo.Input("entity_category", options=ENTITY_CATEGORIES),
                io.Combo.Input("entity_item", options=ALL_ENTITY_ITEMS),
                # 三维图由规则驱动：实体只接收/传递规则，不生成几何描述。
                BLUE_RULE.Input("绘图规则", optional=True),
                BLUE_RULE.Input("尺寸规则", optional=True),
            ],
            outputs=[
                BLUE_ENTITY.Output(),
            ],
        )

    @classmethod
    def execute(
        cls,
        entity_category,
        entity_item,
        JSON=None,
        绘图规则=None,
        尺寸规则=None,
    ) -> io.NodeOutput:
        payload = maybe_json(JSON, JSON)

        if isinstance(payload, dict) and isinstance(payload.get("rules"), list):
            base_rules = collect_rules(*payload["rules"])
        elif payload:
            base_rules = collect_rules(payload)
        else:
            base_rules = []

        # 实体只负责承载连接进来的规则。绘图规则/尺寸规则不会由实体自动补齐。
        connected_rules = collect_rules(base_rules, 绘图规则, 尺寸规则)

        # 后端再次保证第二级对象属于第一级种类。
        category = entity_category if entity_category in ENTITY_ITEMS else ENTITY_CATEGORIES[0]
        valid_items = ENTITY_ITEMS[category]
        item = entity_item if entity_item in valid_items else valid_items[0]
        entity_type = ITEM_ENTITY_TYPE.get(item, "custom")

        geometry = PROCESS_EQUIPMENT_GEOMETRY.get(item)
        # 规则是唯一的三维绘制来源；实体选择本身不产生 draw/size。
        rules = connected_rules

        properties = [
            rule for rule in rules
            if isinstance(rule, dict) and rule.get("rule_kind") != "method"
        ]
        methods = [
            rule for rule in rules
            if isinstance(rule, dict) and rule.get("rule_kind") == "method"
        ]

        entity = {
            # name/entity_type 保留给业务数据、Simulation、Three.js 等下游识别；不再自动产生 UI。
            "name": entity_type,
            "entity_type": entity_type,

            # 新的两级实体语义。
            "entity_category": category,
            "entity_item": item,
            "entity_name": item,

            # 面向对象式规则分组：属性描述“是什么/什么状态”，方法描述“能做什么”。
            "properties": properties,
            "methods": methods,
            # 继续保留 rules，兼容现有 UI/World/Simulation。
            "rules": rules,
        }

        # 设备几何属于 Entity。World 后续只会 deepcopy/组织这份数据，
        # 不再根据 entity_type/entity_item 发明长宽高。
        if geometry:
            entity["geometry"] = deepcopy(geometry)

        return io.NodeOutput(entity)
