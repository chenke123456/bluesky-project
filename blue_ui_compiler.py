from __future__ import annotations

import html
from typing import Any

from .blue_ui_model import compile_ui_model
from .blue_site_state import blank_site_html


def compile_site_html(payload: Any, *, title: str, ui_stream: str, data_stream: str = "BlueNode/data") -> str:
    """Compile the final website shell.

    The shell intentionally does not render components or decide layout. The React
    runtime consumes the UI model and owns DOM/layout. Three.js is loaded by the
    React runtime only when a three.* component is present and enabled by the
    HTML output node's plugin manifest.
    """
    ui = compile_ui_model(payload)
    entities = ui.get("entities", [])

    # No UI entity means no visible site. Do not invent a placeholder UI here.
    if not entities:
        return blank_site_html()

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="/bluenode/runtime.css">
</head>
<body>
<div id="bluenode-runtime">
  <div class="bn-boot">正在加载 BlueNode React Runtime…</div>
</div>
<script type="module" src="/bluenode/runtime.js"></script>
</body>
</html>'''
