import { app } from "/scripts/app.js";

const PROPERTY_RULES = [
    "颜色规则", "二维位置规则", "三维位置规则", "大小规则", "布局规则", "绘制规则", "尺寸规则", "镜头规则", "材料规则", "强度规则", "刚度规则", "时间规则",
    "作用域规则", "拓扑规则", "载荷规则", "稳定性规则", "自定义属性规则",
];

const METHOD_RULES = [
    "传导规则", "生长规则", "碰撞规则", "移动规则", "点击规则",
    "开关规则", "更新规则", "自定义方法规则",
];

const RULE_CONFIG = {
    // 颜色值由后端 COLOR_MAP 动态提供；这里仅保留空占位，避免维护第二份色表。
    "颜色规则": { selectors: [{ label: "颜色值", values: [] }] },
    // 二维/三维位置规则使用专用 Float 输入；不再使用离散位置 Combo。
    "二维位置规则": { selectors: [] },
    "三维位置规则": { selectors: [] },
    "大小规则": { selectors: [
        { label: "宽度", values: ["自动", "25%", "50%", "75%", "100%", "120px", "180px", "240px", "320px", "480px", "640px", "720px", "960px"] },
        { label: "高度", values: ["自动", "25%", "50%", "75%", "100%", "120px", "180px", "240px", "320px", "480px", "640px", "720px", "960px"] },
    ] },
    "布局规则": { selectors: [
        { label: "布局方式", values: ["纵向排列", "横向排列", "网格布局", "左右双栏", "左主右辅", "左辅右主", "顶部+主体", "顶部+双栏", "仪表盘", "自由布局"] },
        { label: "主轴对齐", values: ["起始", "居中", "末尾", "两端对齐", "均匀分布"] },
        { label: "交叉轴对齐", values: ["拉伸", "起始", "居中", "末尾"] },
        { label: "控件间距", values: ["0px", "4px", "8px", "12px", "16px", "24px", "32px", "48px"] },
        { label: "换行方式", values: ["自动换行", "不换行"] },
        { label: "网格列数", values: ["自动", "1列", "2列", "3列", "4列", "6列"] },
    ] },
    "绘制规则": { selectors: [
        { label: "绘制部件", values: ["筒体", "封头", "管板", "折流板"] },
        { label: "轴向", values: ["X轴", "Y轴", "Z轴"] },
        { label: "绘制选项", values: ["开口", "封闭"] },
        { label: "网格分段", values: ["24", "32", "48", "64", "96"] },
    ] },
    // 尺寸规则的实际 selector 会根据第一个“尺寸对象”动态切换。
    "尺寸规则": { selectors: [] },
    "镜头规则": { selectors: [
        { label: "投影模式", values: ["透视", "正交"] },
        { label: "初始视角", values: ["等轴视角", "正视图", "后视图", "左视图", "右视图", "俯视图"] },
        { label: "视野 FOV", values: ["30°", "45°", "50°", "60°", "75°"] },
        { label: "镜头控制", values: ["旋转+平移+缩放", "旋转+缩放", "平移+缩放", "仅旋转", "仅平移", "仅缩放", "锁定"] },
        { label: "最小距离", values: ["0.5", "1", "2", "5", "10"] },
        { label: "最大距离", values: ["10", "20", "50", "100", "200"] },
    ] },
    "材料规则": { selectors: [{ label: "材料选项", values: ["金属", "木材", "玻璃", "塑料", "石材", "织物", "液体", "气体", "自定义材料"] }] },
    "强度规则": { selectors: [
        { label: "强度准则", values: ["Von Mises", "Tresca", "最大主应力", "许用应力"] },
        { label: "安全系数", values: ["1.0", "1.2", "1.5", "2.0", "2.5", "3.0"] },
        { label: "许用应力 (MPa)", values: ["自动", "100", "150", "200", "230", "250", "300", "345", "400", "500"] },
    ] },
    "刚度规则": { selectors: [
        { label: "刚度模型", values: ["线弹性", "轴向", "弯曲", "扭转"] },
        { label: "最大位移 (mm)", values: ["自动", "0.1", "0.2", "0.5", "1.0", "2.0", "5.0", "10.0"] },
    ] },
    "时间规则": { selectors: [{ label: "时间选项", values: ["始终", "白天", "夜间", "开始时", "结束时", "周期性", "自定义时间"] }] },
    "作用域规则": { selectors: [{ label: "作用域选项", values: ["全局", "当前实体", "子级", "父级", "邻近", "局部", "自定义作用域"] }] },
    "拓扑规则": { selectors: [
        { label: "拓扑类型", values: ["线性", "放射状", "网格", "树状", "环状", "完全连接", "断开", "自定义拓扑"] },
        { label: "连接范围", values: ["局部", "全局"] },
    ] },
    "载荷规则": { selectors: [
        { label: "载荷类型", values: ["无载荷", "轻载", "中载", "重载", "拉伸", "压缩", "剪切", "自定义载荷"] },
        { label: "作用方向", values: ["X轴", "Y轴", "Z轴", "法向", "切向", "自定义方向"] },
        { label: "作用范围", values: ["点", "边", "面", "实体", "全局"] },
    ] },
    "稳定性规则": { selectors: [{ label: "稳定性选项", values: ["稳定", "临界", "不稳定", "自动平衡", "锁定", "自定义稳定性"] }] },
    "自定义属性规则": { selectors: [{ label: "属性值", values: ["自定义"] }] },

    "传导规则": { selectors: [{ label: "传导选项", values: ["热传导", "电传导", "力传导", "流体传导", "信号传导", "禁止传导", "自定义传导"] }] },
    "生长规则": { selectors: [{ label: "生长选项", values: ["停止", "缓慢", "正常", "快速", "阶段性", "定向", "自定义生长"] }] },
    "碰撞规则": { selectors: [{ label: "碰撞选项", values: ["允许碰撞", "禁止碰撞", "接触触发", "重叠触发", "保持间距", "自定义碰撞"] }] },
    "移动规则": { selectors: [
        { label: "移动模式", values: ["平移", "目标位置", "往返", "轨道", "旋转", "自定义移动"] },
        { label: "方向", values: ["向左", "向右", "向上", "向下", "X正", "X负", "Y正", "Y负", "Z正", "Z负", "顺时针", "逆时针", "随机", "自定义方向"] },
        { label: "距离", values: ["10px", "25px", "50px", "100px", "200px", "400px", "45deg", "90deg", "180deg", "360deg", "自定义距离"] },
        { label: "速度", values: ["停止", "50px/s", "100px/s", "200px/s", "400px/s", "800px/s", "45deg/s", "90deg/s", "180deg/s", "360deg/s", "自定义速度"] },
        { label: "坐标空间", values: ["本地空间", "世界空间"] },
        { label: "循环方式", values: ["单次", "循环", "往返循环"] },
    ] },
    "点击规则": { selectors: [
        { label: "触发方式", values: ["单击", "双击", "长按", "悬停", "按下", "释放", "自定义触发"] },
        { label: "动作", values: ["无操作", "打开", "关闭", "切换", "提交", "刷新", "选择", "自定义动作"] },
    ] },
    "开关规则": { selectors: [
        { label: "开关动作", values: ["开启", "关闭状态", "切换状态", "自定义开关"] },
        { label: "触发方式", values: ["单击", "数据变化", "事件触发", "自定义触发"] },
    ] },
    "更新规则": { selectors: [
        { label: "更新时机", values: ["立即", "每帧", "每秒", "事件触发", "数据变化", "自定义更新"] },
        { label: "更新动作", values: ["刷新", "提交", "选择", "自定义动作"] },
    ] },
    "自定义方法规则": { selectors: [{ label: "方法值", values: ["自定义"] }] },
};


const LENGTH_VALUES = ["0.01", "0.02", "0.03", "0.04", "0.05", "0.06", "0.08", "0.10", "0.12", "0.15", "0.16", "0.20", "0.25", "0.30", "0.35", "0.40", "0.42", "0.50", "0.60", "0.80", "1.0", "1.2", "1.4", "1.46", "1.5", "1.56", "1.6", "1.8", "2.0", "2.4", "2.8", "3.0", "3.2", "3.4", "3.6", "4.0", "4.6", "4.8", "5.0", "6.0", "8.0", "10.0"];
const THICKNESS_VALUES = ["0.01", "0.02", "0.03", "0.04", "0.05", "0.06", "0.08", "0.10", "0.12", "0.16", "0.20", "0.25", "0.30", "0.40"];
const TUBE_COUNT_VALUES = ["1", "7", "19", "37", "61", "91", "127"];
const CUT_RATIO_VALUES = ["0.15", "0.20", "0.25", "0.30", "0.35", "0.40"];

function sizeRuleSelectors(part) {
    const common = [{ label: "尺寸对象", values: ["筒体", "封头", "管板", "折流板"] }];
    if (part === "封头") return [...common,
        { label: "直径 (m)", values: LENGTH_VALUES },
        { label: "深度 (m)", values: LENGTH_VALUES },
        { label: "厚度 (m)", values: THICKNESS_VALUES },
    ];
    if (part === "管板") return [...common,
        { label: "直径 (m)", values: LENGTH_VALUES },
        { label: "厚度 (m)", values: THICKNESS_VALUES },
        { label: "管孔数量", values: TUBE_COUNT_VALUES },
        { label: "管孔直径 (m)", values: LENGTH_VALUES },
    ];
    if (part === "折流板") return [...common,
        { label: "直径 (m)", values: LENGTH_VALUES },
        { label: "厚度 (m)", values: THICKNESS_VALUES },
        { label: "切口率", values: CUT_RATIO_VALUES },
    ];
    return [...common,
        { label: "直径 (m)", values: LENGTH_VALUES },
        { label: "长度 (m)", values: LENGTH_VALUES },
        { label: "壁厚 (m)", values: THICKNESS_VALUES },
    ];
}

function drawRuleSelectors(part) {
    const common = [
        { label: "绘制部件", values: ["筒体", "封头", "管板", "折流板"] },
        { label: "轴向", values: ["X轴", "Y轴", "Z轴"] },
    ];
    if (part === "封头") return [...common,
        { label: "安装端", values: ["右端", "左端"] },
        { label: "网格分段", values: ["24", "32", "48", "64", "96"] },
    ];
    if (part === "管板") return [...common,
        { label: "管孔显示", values: ["显示管孔", "不显示管孔"] },
        { label: "网格分段", values: ["24", "32", "48", "64", "96"] },
    ];
    if (part === "折流板") return [...common,
        { label: "切口方向", values: ["上切口", "下切口"] },
        { label: "网格分段", values: ["24", "32", "48", "64", "96"] },
    ];
    return [...common,
        { label: "端部", values: ["开口", "封闭"] },
        { label: "网格分段", values: ["24", "32", "48", "64", "96"] },
    ];
}

const OPTION_WIDGET_NAMES = ["rule_option", "rule_option_2", "rule_option_3", "rule_option_4", "rule_option_5", "rule_option_6"];
const POSITION_WIDGET_NAMES = ["position_x", "position_y", "position_z"];
let COLOR_WIDGET_VALUES = [];
let colorOptionsPromise = null;

function loadColorWidgetValues() {
    if (colorOptionsPromise) return colorOptionsPromise;
    colorOptionsPromise = fetch("/bluenode/color-options", { cache: "no-store" })
        .then((response) => {
            if (!response.ok) throw new Error(`color options HTTP ${response.status}`);
            return response.json();
        })
        .then((payload) => {
            const values = Array.isArray(payload?.values) ? payload.values.filter(Boolean) : [];
            if (values.length) COLOR_WIDGET_VALUES = values;
            return COLOR_WIDGET_VALUES;
        })
        .catch((error) => {
            console.warn("[BlueNode] COLOR_MAP 加载失败，使用后端 Combo 当前值作为回退。", error);
            return COLOR_WIDGET_VALUES;
        });
    return colorOptionsPromise;
}

function resizeNodeToWidgets(node) {
    const computed = node.computeSize?.();
    if (!computed) return;
    const width = Math.max(node.size?.[0] ?? 0, computed[0] ?? 0, 320);
    node.setSize?.([width, computed[1] ?? node.size?.[1] ?? 100]);
    node.setDirtyCanvas?.(true, true);
}

function setWidgetVisible(widget, visible) {
    if (!widget) return;
    widget.options ??= {};

    // Keep every backend input widget in node.widgets and only change visibility.
    // ComfyUI serializes prompt inputs by iterating node.widgets; removing/reordering
    // them can make the visible value differ from the value sent to Python.
    if (!("__blueOriginalComputeSize" in widget)) {
        widget.__blueOriginalComputeSize = widget.computeSize;
    }

    widget.hidden = !visible;
    widget.options.hidden = !visible;

    if (visible) {
        if (widget.__blueOriginalComputeSize) {
            widget.computeSize = widget.__blueOriginalComputeSize;
        } else {
            delete widget.computeSize;
        }
    } else {
        widget.computeSize = () => [0, -4];
        // Legacy DOM-backed widgets can otherwise remain floating over the node.
        for (const key of ["element", "inputEl"]) {
            const el = widget[key];
            if (el?.style) el.style.display = "none";
        }
    }

    if (visible) {
        for (const key of ["element", "inputEl"]) {
            const el = widget[key];
            if (el?.style) el.style.display = "";
        }
    }
}

function installDynamicRuleSelectors(node) {
    if (node.__blueRuleSelectorsInstalled) return;
    node.__blueRuleSelectorsInstalled = true;

    const kindWidget = node.widgets?.find((w) => w.name === "rule_kind");
    const nameWidget = node.widgets?.find((w) => w.name === "rule_name");
    if (!kindWidget || !nameWidget) return;

    // Do not reorder backend widgets. Their schema order is already rule_kind -> rule_name
    // -> rule_option... and keeping that order is important for workflow persistence.
    kindWidget.label = "规则类型";
    nameWidget.label = "具体规则";

    const optionWidgetCache = {};
    for (const name of OPTION_WIDGET_NAMES) {
        const widget = node.widgets?.find((w) => w.name === name);
        if (!widget) continue;
        optionWidgetCache[name] = widget;
        // Preserve the native callback. Clearing it breaks value synchronization on
        // newer ComfyUI frontends.
        if (!("__blueNativeCallback" in widget)) widget.__blueNativeCallback = widget.callback;
    }
    node.__blueRuleOptionWidgets = optionWidgetCache;

    const positionWidgetCache = {};
    for (const name of POSITION_WIDGET_NAMES) {
        const widget = node.widgets?.find((w) => w.name === name);
        if (!widget) continue;
        positionWidgetCache[name] = widget;
    }
    node.__bluePositionWidgets = positionWidgetCache;

    loadColorWidgetValues().then(() => {
        if (nameWidget.value === "颜色规则") node.__blueUpdateRuleSelectors?.();
    });

    const updateRuleNames = () => {
        const isMethod = kindWidget.value === "方法";
        const names = isMethod ? METHOD_RULES : PROPERTY_RULES;
        nameWidget.options ??= {};
        nameWidget.options.values = [...names];
        if (!names.includes(nameWidget.value)) nameWidget.value = names[0];
    };

    const updateSelectors = () => {
        updateRuleNames();
        const config = RULE_CONFIG[nameWidget.value] ?? RULE_CONFIG["自定义属性规则"];
        const selectedPart = optionWidgetCache.rule_option?.value || "筒体";
        const is2DPosition = nameWidget.value === "二维位置规则";
        const is3DPosition = nameWidget.value === "三维位置规则";
        const selectors = nameWidget.value === "尺寸规则"
            ? sizeRuleSelectors(selectedPart)
            : nameWidget.value === "绘制规则"
                ? drawRuleSelectors(selectedPart)
                : (config.selectors ?? []);

        // Position vectors use real numeric widgets. 2D exposes X/Y; 3D exposes X/Y/Z.
        POSITION_WIDGET_NAMES.forEach((name, index) => {
            const widget = positionWidgetCache[name];
            if (!widget) return;
            const visible = is3DPosition || (is2DPosition && index < 2);
            setWidgetVisible(widget, visible);
            if (!visible) return;
            widget.label = ["X", "Y", "Z"][index];
            widget.options ??= {};
            widget.options.label = widget.label;
        });

        OPTION_WIDGET_NAMES.forEach((name, index) => {
            const widget = optionWidgetCache[name];
            if (!widget) return;

            const selector = selectors[index];
            const visible = !(is2DPosition || is3DPosition) && Boolean(selector);
            setWidgetVisible(widget, visible);
            if (!visible) return;

            widget.type = "combo";
            widget.label = selector.label;
            widget.options ??= {};
            widget.options.label = selector.label;

            const values = (nameWidget.value === "颜色规则" && index === 0)
                ? COLOR_WIDGET_VALUES
                : selector.values;

            if (Array.isArray(values) && values.length) {
                widget.options.values = [...values];
                if (!widget.options.values.includes(widget.value)) {
                    widget.value = widget.options.values[0];
                }
            }

            // Keep native synchronization. For draw/size rule option #1, refresh the
            // dependent labels/options after the selected primitive changes.
            if (widget.__blueNativeCallback !== undefined) {
                if (index === 0 && (nameWidget.value === "绘制规则" || nameWidget.value === "尺寸规则")) {
                    widget.callback = function (...args) {
                        const result = widget.__blueNativeCallback?.apply(this, args);
                        requestAnimationFrame?.(() => updateSelectors());
                        return result;
                    };
                } else {
                    widget.callback = widget.__blueNativeCallback;
                }
            }
        });

        resizeNodeToWidgets(node);
        node.setDirtyCanvas?.(true, true);
        requestAnimationFrame?.(() => resizeNodeToWidgets(node));
    };

    const kindCallback = kindWidget.callback;
    kindWidget.callback = function (...args) {
        const result = kindCallback?.apply(this, args);
        updateSelectors();
        return result;
    };

    const nameCallback = nameWidget.callback;
    nameWidget.callback = function (...args) {
        const result = nameCallback?.apply(this, args);
        updateSelectors();
        return result;
    };

    node.__blueUpdateRuleSelectors = updateSelectors;
    updateSelectors();
}
app.registerExtension({
    name: "BlueNode.RulePropertyMethodSelectors",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "BlueRuleNode") return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = originalOnNodeCreated?.apply(this, args);
            installDynamicRuleSelectors(this);
            return result;
        };

        const originalOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = originalOnConfigure?.apply(this, args);
            this.__blueUpdateRuleSelectors?.();
            requestAnimationFrame?.(() => this.__blueUpdateRuleSelectors?.());
            return result;
        };
    },
});
