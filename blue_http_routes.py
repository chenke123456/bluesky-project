from __future__ import annotations

import json
from pathlib import Path

import folder_paths
from aiohttp import web
from server import PromptServer

from .blue_html_output_node import BlueHtmlOutputNode
from .blue_rule_node import COLOR_MAP
from .blue_ui_model import build_data_context, compile_ui_model
from .blue_site_state import (
    GENERATED_WEB_DIR,
    atomic_write_text,
    blank_site_html,
    generated_site_paths,
    is_ui_stream,
    read_site_state,
    state_is_current_and_active,
    write_site_state,
)


_PLUGIN_DIR = Path(__file__).resolve().parent
_HTML_DIR = _PLUGIN_DIR / "html"
_LIVE_HTML = _HTML_DIR / "live.html"
_RUNTIME_JS = _HTML_DIR / "runtime.js"
_RUNTIME_CSS = _HTML_DIR / "runtime.css"
_NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}


@PromptServer.instance.routes.get("/bluenode/live")
async def bluenode_live_page(request: web.Request) -> web.StreamResponse:
    """Serve the fixed compiler/runtime shell from the plugin html directory."""
    if not _LIVE_HTML.is_file():
        return web.Response(status=404, text="BlueNode html/live.html not found")
    return web.FileResponse(_LIVE_HTML, headers=_NO_CACHE)


@PromptServer.instance.routes.get("/bluenode/runtime.js")
async def bluenode_runtime_js(request: web.Request) -> web.StreamResponse:
    if not _RUNTIME_JS.is_file():
        return web.Response(status=404, text="BlueNode html/runtime.js not found")
    return web.FileResponse(_RUNTIME_JS, headers={**_NO_CACHE, "Content-Type": "text/javascript; charset=utf-8"})


@PromptServer.instance.routes.get("/bluenode/runtime.css")
async def bluenode_runtime_css(request: web.Request) -> web.StreamResponse:
    if not _RUNTIME_CSS.is_file():
        return web.Response(status=404, text="BlueNode html/runtime.css not found")
    return web.FileResponse(_RUNTIME_CSS, headers={**_NO_CACHE, "Content-Type": "text/css; charset=utf-8"})


@PromptServer.instance.routes.get("/bluenode/color-options")
async def bluenode_color_options(request: web.Request) -> web.Response:
    """Expose the rule color palette from the single backend COLOR_MAP source."""
    return _json_response(
        {
            "ok": True,
            "values": list(COLOR_MAP.keys()),
            "colors": [{"name": name, "hex": value} for name, value in COLOR_MAP.items()],
        }
    )


@PromptServer.instance.routes.get("/bluenode/live-data")
async def bluenode_live_data(request: web.Request) -> web.Response:
    """Return raw JSON plus two framework-neutral projections.

    - data_context: lets a UI runtime know entity count/types/objects in backend JSON.
    - ui_model: interprets the same existing Entity + Rule pack as UI IR.

    This keeps all existing Rule/Entity node interfaces unchanged.
    """
    requested_stream = request.rel_url.query.get("stream", "BlueNode/simulation")
    relative_prefix = BlueHtmlOutputNode._safe_relative_prefix(requested_stream)

    output_root = Path(folder_paths.get_output_directory()).resolve()
    target_dir = (output_root / relative_prefix.parent).resolve()

    if output_root != target_dir and output_root not in target_dir.parents:
        return _json_response({"ok": False, "error": "非法的数据路径"}, status=400)

    stem = relative_prefix.name or "simulation"
    json_path = target_dir / f"{stem}_live.json"
    meta_path = target_dir / f"{stem}_live.meta.json"

    if not json_path.is_file():
        return _json_response(
            {
                "ok": False,
                "error": f"尚未生成 {relative_prefix.as_posix()} 的实时 JSON",
                "stream": relative_prefix.as_posix(),
            },
            status=404,
        )

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as error:
        return _json_response({"ok": False, "error": f"读取 JSON 失败：{error}"}, status=500)

    meta = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    return _json_response(
        {
            "ok": True,
            "stream": relative_prefix.as_posix(),
            "title": meta.get("title", "BlueNode 实时数据"),
            "updated_at": meta.get("updated_at"),
            "data": data,
            "data_context": build_data_context(data),
            "ui_model": compile_ui_model(data),
        }
    )


def _json_response(payload: dict, status: int = 200) -> web.Response:
    return web.Response(
        status=status,
        text=json.dumps(payload, ensure_ascii=False, default=str),
        content_type="application/json",
        headers=_NO_CACHE,
    )

@PromptServer.instance.routes.post("/bluenode/clear-site")
async def bluenode_clear_site(request: web.Request) -> web.Response:
    """Invalidate a generated UI site when its workflow input is disconnected/removed."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    requested_stream = str(body.get("stream") or "BlueNode/ui")
    relative_prefix = BlueHtmlOutputNode._safe_relative_prefix(requested_stream)
    if not is_ui_stream(relative_prefix):
        return _json_response({"ok": True, "ignored": True, "stream": relative_prefix.as_posix()})

    site_path, state_path, _ = generated_site_paths(relative_prefix)
    atomic_write_text(site_path, blank_site_html())
    write_site_state(
        state_path,
        stream=relative_prefix.as_posix(),
        active=False,
        entity_count=0,
        reason=str(body.get("reason") or "workflow-disconnected"),
    )

    # Keep the UI stream consistent with the visible site: disconnected UI means zero entities.
    output_root = Path(folder_paths.get_output_directory()).resolve()
    target_dir = (output_root / relative_prefix.parent).resolve()
    if output_root == target_dir or output_root in target_dir.parents:
        stem = relative_prefix.name or "ui"
        json_path = target_dir / f"{stem}_live.json"
        meta_path = target_dir / f"{stem}_live.meta.json"
        atomic_write_text(json_path, '{"entities": []}\n')
        atomic_write_text(
            meta_path,
            json.dumps(
                {
                    "title": "",
                    "stream": relative_prefix.as_posix(),
                    "active": False,
                    "reason": str(body.get("reason") or "workflow-disconnected"),
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
        )

    return _json_response({"ok": True, "stream": relative_prefix.as_posix(), "active": False})


@PromptServer.instance.routes.get("/bluenode/site")
async def bluenode_generated_site(request: web.Request) -> web.StreamResponse:
    """Serve only the site generated by the current server session and current UI state.

    Old materialized HTML is never treated as current merely because the file still exists.
    """
    requested_stream = request.rel_url.query.get("stream", "BlueNode/ui")
    relative_prefix = BlueHtmlOutputNode._safe_relative_prefix(requested_stream)
    if not is_ui_stream(relative_prefix):
        return web.Response(status=400, text="该 stream 不是 UI stream")

    site_path, state_path, _site_rel = generated_site_paths(relative_prefix)
    state = read_site_state(state_path)

    # No current active UI => deliberately blank page. This also rejects files from a prior server session.
    if not state_is_current_and_active(state):
        return web.Response(
            text=blank_site_html(),
            content_type="text/html",
            charset="utf-8",
            headers=_NO_CACHE,
        )

    if not site_path.is_file():
        return web.Response(
            text=blank_site_html(),
            content_type="text/html",
            charset="utf-8",
            headers=_NO_CACHE,
        )

    return web.FileResponse(site_path, headers=_NO_CACHE)
