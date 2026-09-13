import { app } from "/scripts/app.js";

const CATEGORY_ITEMS = {
    "设备": ["风扇", "空调", "灯", "摄像头", "传感器", "开关", "显示器", "音箱", "路由器", "服务器", "电机", "水泵", "发电机", "机器人", "车辆", "通用设备"],
    "家具": ["桌子", "椅子", "沙发", "床", "柜子", "书架", "茶几", "餐桌", "工作台", "灯具", "装饰物", "通用家具"],
    "网站": ["页面", "面板", "按钮", "分隔线", "控件", "卡片", "人物信息", "状态", "指示器", "装饰", "3D视图"],
    "系统": ["机械系统", "电子系统", "木工系统", "液压系统", "气动系统", "电力系统", "控制系统", "通信系统", "时间系统", "天气系统", "环境系统", "交通系统", "经济系统", "阴阳系统", "五行系统", "河图洛书系统", "自定义系统"],
    "机械部件": ["法兰", "齿轮", "轴", "轴承", "联轴器", "皮带轮", "链轮", "弹簧", "凸轮", "丝杠", "导轨", "紧固件", "通用机械部件"],
    "化工设备": ["压力容器", "储罐", "罐子", "冷凝器", "再沸器", "封头", "筒体", "折流板", "管板", "列管", "通用化工设备"],
    "电子元件": ["电阻", "电容", "电感", "二极管", "三极管", "MOS管", "继电器", "芯片", "传感器元件", "连接器", "电路板", "通用电子元件"],
    "木工对象": ["木板", "木方", "榫头", "榫眼", "柜体", "门板", "抽屉", "层板", "木框", "木工连接件", "通用木工对象"],
    "建筑": ["房屋", "房间", "门", "墙", "住宅", "办公楼", "商业建筑", "工厂", "仓库", "学校", "医院", "道路", "桥梁", "通用建筑"],
    "人物": ["市民", "工人", "学生", "医生", "教师", "顾客", "游客", "驾驶员", "通用人物"],
    "自然": ["树木", "花草", "动物", "微生物", "天气", "水体", "山体", "通用自然对象"],
    "3D对象": ["3D场景", "3D模型", "机械模型", "建筑模型", "车辆模型", "地形", "通用3D对象"],
    "自定义": ["自定义实体"],
};

function syncEntityItem(node) {
    const categoryWidget = node.widgets?.find((w) => w.name === "entity_category");
    const itemWidget = node.widgets?.find((w) => w.name === "entity_item");
    if (!categoryWidget || !itemWidget) return;

    const values = CATEGORY_ITEMS[categoryWidget.value] || CATEGORY_ITEMS["设备"];
    itemWidget.options = itemWidget.options || {};
    itemWidget.options.values = values;

    if (!values.includes(itemWidget.value)) {
        itemWidget.value = values[0];
    }
    node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
    name: "BlueNode.EntityCategoryItem",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "BlueEntityNode") return;

        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const result = originalCreated?.apply(this, arguments);

            const categoryWidget = this.widgets?.find((w) => w.name === "entity_category");
            if (categoryWidget) {
                const oldCallback = categoryWidget.callback;
                categoryWidget.callback = (...args) => {
                    const value = oldCallback?.apply(categoryWidget, args);
                    syncEntityItem(this);
                    return value;
                };
            }

            // 等 ComfyUI 恢复完工作流 widget 值后再同步一次。
            setTimeout(() => syncEntityItem(this), 0);
            return result;
        };
    },
});
