from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple


PLUGIN_DIR = Path(__file__).resolve().parent
GENERATED_WEB_DIR = (PLUGIN_DIR / "web" / "generated").resolve()
SERVER_SESSION_ID = uuid.uuid4().hex


def is_ui_stream(relative_prefix: Path) -> bool:
    stem = (relative_prefix.name or "ui").lower()
    return stem in {"ui", "site", "website", "web"} or "ui" in stem


def generated_site_paths(relative_prefix: Path) -> Tuple[Path, Path, Path]:
    """Return (site_html, state_json, site_relative_path) inside web/generated."""
    parts = list(relative_prefix.parts)
    if parts and parts[0].lower() == "bluenode":
        parts = parts[1:]
    if not parts:
        parts = ["ui"]

    site_rel = Path(*parts[:-1]) / f"{parts[-1]}_site.html"
    site_path = (GENERATED_WEB_DIR / site_rel).resolve()
    if GENERATED_WEB_DIR != site_path.parent and GENERATED_WEB_DIR not in site_path.parents:
        site_rel = Path("ui_site.html")
        site_path = GENERATED_WEB_DIR / site_rel

    state_path = site_path.with_suffix(".state.json")
    return site_path, state_path, site_rel


def blank_site_html() -> str:
    """A deliberately blank document. No visible UI may be invented by the compiler."""
    return "<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"></head><body></body></html>\n"


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def write_site_state(
    state_path: Path,
    *,
    stream: str,
    active: bool,
    entity_count: int,
    updated_at: str | None = None,
    reason: str | None = None,
) -> None:
    payload: Dict[str, Any] = {
        "session_id": SERVER_SESSION_ID,
        "stream": stream,
        "active": bool(active),
        "entity_count": int(entity_count),
    }
    if updated_at:
        payload["updated_at"] = updated_at
    if reason:
        payload["reason"] = reason
    atomic_write_text(state_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_site_state(state_path: Path) -> Dict[str, Any]:
    if not state_path.is_file():
        return {}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def state_is_current_and_active(state: Dict[str, Any]) -> bool:
    return bool(
        state
        and state.get("session_id") == SERVER_SESSION_ID
        and state.get("active") is True
        and int(state.get("entity_count") or 0) > 0
    )
