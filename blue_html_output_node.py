from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote

import folder_paths
from comfy_api.latest import io

from .blue_core import BLUE_JSON, maybe_json
from .blue_ui_compiler import compile_site_html
from .blue_ui_model import compile_ui_model
from .blue_site_state import (
    generated_site_paths,
    is_ui_stream,
    write_site_state,
)


class BlueHtmlOutputNode(io.ComfyNode):
    """输出实时 JSON，并根据 UI JSON 中实际使用的组件按需启用网页插件。

    这个节点只负责：
      1. 保存输入 JSON；
      2. 扫描全部 JSON / UI Model；
      3. if 判断是否需要 React / Three.js；
      4. 调用现有底层 compiler 生成页面壳；
      5. 把插件 manifest 交给网页运行时。

    页面布局、组件结构、CSS 和具体渲染行为仍由底层 React Runtime / Three.js Renderer 决定。
    """


    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="BlueHtmlOutputNode",
            display_name="HTML 输出（插件实时网页）",
            category="Blue/Output",
            inputs=[
                BLUE_JSON.Input("JSON"),
                io.String.Input("title", default="BlueNode 模拟数据"),
                io.String.Input("filename_prefix", default="BlueNode/simulation"),
            ],
            outputs=[
                io.String.Output(),  # 插件 web/generated 内生成网站的磁盘路径
                io.String.Output(),  # 通过 ComfyUI 打开的 URL
            ],
        )

    @staticmethod
    def _safe_relative_prefix(value: str) -> Path:
        """允许 output 下的子目录，但禁止路径穿越。"""
        raw = str(value or "BlueNode/simulation").replace("\\", "/").strip()
        parts = []
        for part in raw.split("/"):
            part = part.strip()
            if not part or part in {".", ".."}:
                continue
            part = re.sub(r'[<>:"|?*\x00-\x1f]', "_", part)
            parts.append(part)

        if not parts:
            parts = ["BlueNode", "simulation"]
        return Path(*parts)

    @staticmethod
    def _json_text(value: Any) -> str:
        payload = maybe_json(value, value)
        try:
            return json.dumps(payload, ensure_ascii=False, indent=2, default=str)
        except Exception:
            return json.dumps(str(payload), ensure_ascii=False, indent=2)

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        """先写临时文件再替换，避免网页轮询时读到半截 JSON。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        temp_path.write_text(text, encoding="utf-8")
        temp_path.replace(path)

    @classmethod
    def _detect_plugins(cls, payload: Any, ui_model: Any = None) -> Dict[str, bool]:
        """Determine React / Three.js only from website UI entities.

        Non-website entities (设备/人物/家具/建筑/自然...) are data. They may be
        passed to UI or Three.js through DATA_CONTEXT, but they do not trigger a UI
        component merely because their legacy entity_type resembles one.
        """
        plugins = {"react": False, "three": False}

        def inspect_renderer(renderer: Any) -> None:
            name = str(renderer or "").strip().lower()
            if name == "react" or name.startswith("react."):
                plugins["react"] = True
            if name == "three" or name.startswith("three.") or "three.js" in name:
                plugins["three"] = True

        def inspect_component(component: Any) -> None:
            name = str(component or "").strip().lower()
            if name == "react" or name.startswith("react."):
                plugins["react"] = True
            if name == "three" or name.startswith("three.") or name.startswith("threejs."):
                plugins["three"] = True

        # UI Model 已经过滤掉所有非“网站”实体，因此它是插件分发的权威来源。
        if isinstance(ui_model, dict):
            entities = ui_model.get("entities", []) or []
            if entities:
                plugins["react"] = True
            for entity in entities:
                if not isinstance(entity, dict):
                    continue
                view = entity.get("view")
                if isinstance(view, dict):
                    inspect_renderer(view.get("renderer"))
                    inspect_component(view.get("component"))
            return plugins

        # 编译 UI Model 失败时的保底扫描：仍然只扫描 category=网站 的实体。
        raw = maybe_json(payload, payload)
        entities = []
        if isinstance(raw, dict) and isinstance(raw.get("entities"), list):
            entities = raw.get("entities") or []
        elif isinstance(raw, list):
            entities = raw
        elif isinstance(raw, dict):
            entities = [raw]

        for entity in entities:
            if not isinstance(entity, dict):
                continue
            if str(entity.get("entity_category") or "").strip() != "网站":
                continue
            plugins["react"] = True
            inspect_renderer(entity.get("renderer"))
            inspect_component(entity.get("component"))
            view = entity.get("view")
            if isinstance(view, dict):
                inspect_renderer(view.get("renderer"))
                inspect_component(view.get("component"))
            if str(entity.get("entity_item") or "").strip() == "3D视图":
                plugins["three"] = True

        return plugins

    @classmethod
    def _apply_plugin_dispatch(cls, site_html: str, plugins: Dict[str, bool]) -> str:
        """把插件判断结果交给网页运行时，不参与布局。

        React / Three.js 的实际 import 在 runtime.js 内按 manifest 做惰性加载。
        HTML 输出节点只负责 if 判断并写入 manifest。
        """
        html_text = str(site_html or "")

        manifest = json.dumps(
            {
                "react": bool(plugins.get("react")),
                "three": bool(plugins.get("three")),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).replace("</", "<\\/")
        manifest_tag = (
            '<script type="application/json" id="bluenode-plugin-manifest">'
            f"{manifest}</script>\n"
        )

        # 防止重复编译时积累旧 manifest。
        html_text = re.sub(
            r'<script\s+type=["\']application/json["\']\s+id=["\']bluenode-plugin-manifest["\']>.*?</script>\s*',
            '',
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if "</head>" in html_text:
            html_text = html_text.replace("</head>", manifest_tag + "</head>", 1)
        else:
            html_text = manifest_tag + html_text

        return html_text

    @classmethod
    def execute(
        cls,
        JSON=None,
        title="BlueNode 模拟数据",
        filename_prefix="BlueNode/simulation",
    ) -> io.NodeOutput:
        output_root = Path(folder_paths.get_output_directory()).resolve()
        relative_prefix = cls._safe_relative_prefix(filename_prefix)

        subdir = relative_prefix.parent
        stem = relative_prefix.name or "simulation"
        target_dir = (output_root / subdir).resolve()

        # 最终运行时 JSON 仍放 ComfyUI/output；HTML 本身固定放插件目录。
        if output_root != target_dir and output_root not in target_dir.parents:
            relative_prefix = Path("BlueNode") / "simulation"
            subdir = relative_prefix.parent
            stem = relative_prefix.name
            target_dir = (output_root / subdir).resolve()

        target_dir.mkdir(parents=True, exist_ok=True)

        json_path = target_dir / f"{stem}_live.json"
        meta_path = target_dir / f"{stem}_live.meta.json"
        html_path = Path(__file__).resolve().parent / "html" / "live.html"

        payload = maybe_json(JSON, JSON)
        json_text = cls._json_text(payload)
        updated_at = datetime.now().astimezone().isoformat(timespec="seconds")

        # 原始业务 JSON 单独保存，网页通过插件 HTTP 接口读取它。
        cls._atomic_write_text(json_path, json_text + "\n")

        # UI 流会在下面进一步扫描组件；data 流没有页面组件，不加载 React / Three.js。
        ui_stream = is_ui_stream(relative_prefix)
        plugins: Dict[str, bool] = {"react": False, "three": False}
        ui_model = None
        if ui_stream:
            try:
                ui_model = compile_ui_model(payload)
                plugins = cls._detect_plugins(payload, ui_model)
            except Exception:
                # 编译错误由下面原有 UI compile error 路径统一处理。
                plugins = cls._detect_plugins(payload)

        cls._atomic_write_text(
            meta_path,
            json.dumps(
                {
                    "title": str(title or "BlueNode 模拟数据"),
                    "updated_at": updated_at,
                    "stream": relative_prefix.as_posix(),
                    "plugins": plugins,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )

        # UI 流额外编译成真正的网站文件。
        # 网页输出节点只负责插件分发；页面布局完全由现有底层 compiler 决定。
        site_path, state_path, _site_rel = generated_site_paths(relative_prefix)
        if ui_stream:
            try:
                if ui_model is None:
                    ui_model = compile_ui_model(payload)
                    plugins = cls._detect_plugins(payload, ui_model)

                entity_count = len(ui_model.get("entities", []))
                site_html = compile_site_html(
                    payload,
                    title=str(title or "BlueNode Generated Website"),
                    ui_stream=relative_prefix.as_posix(),
                    data_stream="BlueNode/data",
                )

                # 这里仅做 if 插件判断/加载开关，不修改布局。
                site_html = cls._apply_plugin_dispatch(site_html, plugins)

                cls._atomic_write_text(site_path, site_html)
                write_site_state(
                    state_path,
                    stream=relative_prefix.as_posix(),
                    active=entity_count > 0,
                    entity_count=entity_count,
                    updated_at=updated_at,
                    reason=None if entity_count > 0 else "empty-ui-model",
                )
            except Exception as error:
                write_site_state(
                    state_path,
                    stream=relative_prefix.as_posix(),
                    active=False,
                    entity_count=0,
                    updated_at=updated_at,
                    reason=f"compile-error: {error}",
                )
                print(f"[BlueNode] UI site compile failed: {error}")

        stream = quote(relative_prefix.as_posix(), safe="")
        if ui_stream:
            live_url = f"/bluenode/site?stream={stream}&data=BlueNode%2Fdata"
            return io.NodeOutput(str(site_path), live_url)

        live_url = f"/bluenode/live?stream={stream}"
        return io.NodeOutput(str(html_path), live_url)
