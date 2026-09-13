import { app } from "/scripts/app.js";

/**
 * Generated-site lifecycle guard.
 *
 * IMPORTANT:
 * ComfyUI may temporarily report an input as disconnected while a workflow is
 * being configured/reloaded. Never clear the generated UI immediately from
 * that transient state, otherwise a freshly generated BlueNode/ui can be
 * erased after a successful queue run.
 */
function streamOf(node) {
    const widget = node.widgets?.find((w) => w.name === "filename_prefix");
    return String(widget?.value || "BlueNode/ui");
}

function isUiStream(stream) {
    const stem = String(stream || "").replace(/\\/g, "/").split("/").filter(Boolean).at(-1)?.toLowerCase() || "";
    return ["ui", "site", "website", "web"].includes(stem) || stem.includes("ui");
}

function hasConnectedJson(node) {
    const input = node?.inputs?.find((item) => item?.name === "JSON") || node?.inputs?.[0];
    return Boolean(input && input.link != null);
}

function graphHasLiveUiOutput(stream, exceptNode = null) {
    const graphNodes = app?.graph?._nodes || [];
    return graphNodes.some((node) => {
        if (!node || node === exceptNode) return false;
        const type = node.comfyClass || node.type || node.constructor?.comfyClass;
        if (type !== "BlueHtmlOutputNode") return false;
        return streamOf(node) === stream && hasConnectedJson(node);
    });
}

async function clearSite(stream, reason) {
    if (!isUiStream(stream)) return;
    try {
        await fetch("/bluenode/clear-site", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stream, reason }),
            cache: "no-store",
        });
    } catch (error) {
        console.warn("[BlueNode] clear generated site failed", error);
    }
}

function cancelPendingClear(node) {
    if (node?.__bluePendingClearTimer) {
        clearTimeout(node.__bluePendingClearTimer);
        node.__bluePendingClearTimer = null;
    }
}

function scheduleVerifiedClear(node, stream, reason, delay = 1200) {
    cancelPendingClear(node);
    node.__bluePendingClearTimer = setTimeout(() => {
        node.__bluePendingClearTimer = null;

        // A transient ComfyUI disconnect has already recovered: do nothing.
        if (hasConnectedJson(node)) return;

        // Another connected HTML output owns the same UI stream: never erase it.
        if (graphHasLiveUiOutput(stream, node)) return;

        clearSite(stream, reason);
    }, delay);
}

function installSiteLifecycle(node) {
    if (node.__blueSiteLifecycleInstalled) return;
    node.__blueSiteLifecycleInstalled = true;
    node.__blueLastSiteStream = streamOf(node);

    const prefixWidget = node.widgets?.find((w) => w.name === "filename_prefix");
    if (prefixWidget) {
        const originalCallback = prefixWidget.callback;
        prefixWidget.callback = function (...args) {
            const oldStream = node.__blueLastSiteStream || streamOf(node);
            const result = originalCallback?.apply(this, args);
            const newStream = streamOf(node);
            node.__blueLastSiteStream = newStream;

            // Renaming is deliberate. Only clear the old stream after verifying
            // that no other connected output node still owns it.
            if (oldStream !== newStream && !graphHasLiveUiOutput(oldStream, node)) {
                clearSite(oldStream, "stream-renamed");
            }
            return result;
        };
    }

    const originalConnectionsChange = node.onConnectionsChange;
    node.onConnectionsChange = function (type, index, connected, linkInfo, slotInfo) {
        const result = originalConnectionsChange?.apply(this, arguments);
        if (type === 1) {
            const input = this.inputs?.[index];
            if (input?.name === "JSON" || index === 0) {
                if (connected) {
                    cancelPendingClear(this);
                } else {
                    // Do not clear immediately: workflow loading/configuration can
                    // produce a temporary disconnected state for one or more frames.
                    scheduleVerifiedClear(this, streamOf(this), "ui-input-disconnected");
                }
            }
        }
        return result;
    };

    const originalRemoved = node.onRemoved;
    node.onRemoved = function (...args) {
        cancelPendingClear(this);
        const removedStream = streamOf(this);
        const result = originalRemoved?.apply(this, args);

        // Give ComfyUI time to finish graph replacement. If a replacement node
        // with the same stream exists, preserve the generated UI.
        setTimeout(() => {
            if (!graphHasLiveUiOutput(removedStream, null)) {
                clearSite(removedStream, "ui-output-node-removed");
            }
        }, 1200);
        return result;
    };
}

app.registerExtension({
    name: "BlueNode.GeneratedSiteLifecycle",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "BlueHtmlOutputNode") return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = originalOnNodeCreated?.apply(this, args);
            installSiteLifecycle(this);
            return result;
        };

        const originalOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = originalOnConfigure?.apply(this, args);
            installSiteLifecycle(this);
            this.__blueLastSiteStream = streamOf(this);

            // Intentionally DO NOT clear here. During onConfigure ComfyUI may not
            // have restored links yet. Clearing here caused the first-run/second-run
            // disappearance bug.
            return result;
        };
    },
});
