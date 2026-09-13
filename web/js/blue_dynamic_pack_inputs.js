import { app } from "/scripts/app.js";

/**
 * 规则包 / 实体包动态输入槽。
 *
 * 后端预留 24 个 optional 输入，但前端默认只展示 3 个。
 * 最后一行始终是“+”槽：
 *   1. 点击“+”行 -> 新增一个空输入槽；
 *   2. 直接把连线拖到“+” -> “+”自动变成新的编号输入，并继续生成下一个“+”。
 */
const PACK_CONFIG = {
    BlueRulePackNode: {
        prefix: "rule_",
        type: "JSON",
        maxInputs: 24,
    },
    BlueEntityPackNode: {
        prefix: "entity_",
        type: "JSON",
        maxInputs: 24,
    },
};

const DEFAULT_VISIBLE = 3;
const PLUS_NAME = "+";

function resizeNode(node) {
    const size = node.computeSize?.();
    if (!size) return;

    const width = Math.max(node.size?.[0] ?? 0, size[0] ?? 0, 210);
    node.setSize?.([width, size[1]]);
    node.setDirtyCanvas?.(true, true);
}

function numberedIndex(name, prefix) {
    if (typeof name !== "string" || !name.startsWith(prefix)) return null;
    const value = Number(name.slice(prefix.length));
    return Number.isInteger(value) && value > 0 ? value : null;
}

function realInputs(node, config) {
    return (node.inputs ?? [])
        .filter((input) => numberedIndex(input?.name, config.prefix) !== null)
        .sort(
            (a, b) =>
                numberedIndex(a.name, config.prefix) -
                numberedIndex(b.name, config.prefix)
        );
}

function highestRealIndex(node, config) {
    return realInputs(node, config).reduce(
        (max, input) => Math.max(max, numberedIndex(input.name, config.prefix) ?? 0),
        0
    );
}

function removeInputByIndex(node, index) {
    if (index < 0 || index >= (node.inputs?.length ?? 0)) return;
    // 只移除无连接的预留槽。已连接槽绝不自动删除。
    if (node.inputs[index]?.link != null) return;
    node.removeInput?.(index);
}

function compactInitialInputs(node, config) {
    // 后端会创建 24 个槽。这里只保留默认 3 个，以及任何已经有连接的槽。
    // 倒序删除避免 index 位移。
    for (let i = (node.inputs?.length ?? 0) - 1; i >= 0; i--) {
        const input = node.inputs[i];
        const n = numberedIndex(input?.name, config.prefix);
        if (n !== null && n > DEFAULT_VISIBLE && input.link == null) {
            removeInputByIndex(node, i);
        }
    }
}

function ensurePlus(node, config) {
    if ((node.inputs ?? []).some((input) => input?.name === PLUS_NAME)) return;
    if (highestRealIndex(node, config) >= config.maxInputs) return;

    node.addInput?.(PLUS_NAME, config.type);
    const plus = node.inputs?.[node.inputs.length - 1];
    if (plus) {
        plus.label = PLUS_NAME;
        plus.__blueDynamicPlus = true;
    }
}

function sortInputs(node, config) {
    const inputs = node.inputs ?? [];
    const numbered = inputs
        .filter((input) => numberedIndex(input?.name, config.prefix) !== null)
        .sort(
            (a, b) =>
                numberedIndex(a.name, config.prefix) -
                numberedIndex(b.name, config.prefix)
        );
    const other = inputs.filter(
        (input) =>
            numberedIndex(input?.name, config.prefix) === null &&
            input?.name !== PLUS_NAME
    );
    const plus = inputs.find((input) => input?.name === PLUS_NAME);
    node.inputs = [...numbered, ...other, ...(plus ? [plus] : [])];
}

function expandOne(node, config, promotePlus = false) {
    const nextIndex = highestRealIndex(node, config) + 1;
    if (nextIndex > config.maxInputs) return false;

    const name = `${config.prefix}${nextIndex}`;
    const existing = (node.inputs ?? []).find((input) => input?.name === name);
    if (existing) return false;

    const plusIndex = (node.inputs ?? []).findIndex((input) => input?.name === PLUS_NAME);
    const plus = plusIndex >= 0 ? node.inputs[plusIndex] : null;

    if (promotePlus && plus) {
        // 连线已经接到了 + 槽：直接把这个槽提升成正式编号槽，连接不会丢。
        plus.name = name;
        plus.label = name;
        plus.__blueDynamicPlus = false;
    } else {
        node.addInput?.(name, config.type);
        const added = node.inputs?.pop();
        if (added) {
            added.label = name;
            const insertAt = plusIndex >= 0 ? plusIndex : node.inputs.length;
            node.inputs.splice(insertAt, 0, added);
        }
    }

    ensurePlus(node, config);
    sortInputs(node, config);
    resizeNode(node);
    requestAnimationFrame?.(() => resizeNode(node));
    return true;
}

function installDynamicInputs(node, config) {
    if (node.__blueDynamicPackInputsInstalled) return;
    node.__blueDynamicPackInputsInstalled = true;

    compactInitialInputs(node, config);
    ensurePlus(node, config);
    sortInputs(node, config);
    resizeNode(node);

    // 直接拖一根线到“+”槽时，自动把 + 变成 rule_N/entity_N，再生成新的 +。
    const originalConnectionsChange = node.onConnectionsChange;
    node.onConnectionsChange = function (type, index, connected, linkInfo, slotInfo) {
        const result = originalConnectionsChange?.apply(this, arguments);
        if (connected && type === 1) {
            const input = this.inputs?.[index];
            if (input?.name === PLUS_NAME) {
                expandOne(this, config, true);
            }
        }
        return result;
    };

    // 同时允许直接点击“+”这一行来增加空槽。
    const originalMouseDown = node.onMouseDown;
    node.onMouseDown = function (event, pos, canvas) {
        const plusIndex = (this.inputs ?? []).findIndex((input) => input?.name === PLUS_NAME);
        if (plusIndex >= 0 && Array.isArray(pos)) {
            try {
                const connectionPos = this.getConnectionPos?.(true, plusIndex, [0, 0]);
                if (connectionPos) {
                    const localY = connectionPos[1] - (this.pos?.[1] ?? 0);
                    // 左侧输入区域点击 + 行即可扩展；保留连接圆点本身的原生拖线行为。
                    if (pos[0] > 14 && pos[0] < 120 && Math.abs(pos[1] - localY) <= 10) {
                        expandOne(this, config, false);
                        return true;
                    }
                }
            } catch (_) {
                // LiteGraph 版本差异时仍保留“拖线到 +”的扩展方式。
            }
        }
        return originalMouseDown?.apply(this, arguments);
    };

    node.__blueRefreshDynamicPackInputs = () => {
        // 配置/工作流恢复后，把已存在的编号槽保留下来，只清理未使用的远端预留槽。
        const usedIndices = realInputs(node, config)
            .filter((input) => input.link != null)
            .map((input) => numberedIndex(input.name, config.prefix));
        const visibleThrough = Math.max(DEFAULT_VISIBLE, ...usedIndices, 0);

        for (let i = (node.inputs?.length ?? 0) - 1; i >= 0; i--) {
            const input = node.inputs[i];
            const n = numberedIndex(input?.name, config.prefix);
            if (n !== null && n > visibleThrough && input.link == null) {
                removeInputByIndex(node, i);
            }
        }
        ensurePlus(node, config);
        sortInputs(node, config);
        resizeNode(node);
    };
}

app.registerExtension({
    name: "BlueNode.DynamicPackInputs",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        const config = PACK_CONFIG[nodeData.name];
        if (!config) return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = originalOnNodeCreated?.apply(this, args);
            installDynamicInputs(this, config);
            return result;
        };

        const originalOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = originalOnConfigure?.apply(this, args);
            this.__blueRefreshDynamicPackInputs?.();
            requestAnimationFrame?.(() => this.__blueRefreshDynamicPackInputs?.());
            return result;
        };
    },
});
