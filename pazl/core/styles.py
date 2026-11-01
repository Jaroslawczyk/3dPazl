"""Architectural style presets (YAML in pazl/styles)."""
from __future__ import annotations

from pathlib import Path

import yaml

DIR = Path(__file__).parent.parent / "styles"
_STYLES: dict[str, dict] = {}


def load_styles(force=False) -> dict[str, dict]:
    if _STYLES and not force:
        return _STYLES
    _STYLES.clear()
    for f in sorted(DIR.glob("*.yaml")):
        data = yaml.safe_load(f.read_text("utf-8")) or {}
        data.setdefault("id", f.stem)
        _STYLES[data["id"]] = data
    _STYLES.setdefault("generic", {"id": "generic", "name": "Generic", "materials": {}, "defaults": {}})
    return _STYLES


def get_style(sid: str) -> dict:
    s = load_styles()
    return s.get(sid) or s["generic"]


def summary() -> list[dict]:
    return [{"id": s["id"], "name": s.get("name"), "name_ru": s.get("name_ru"), "era": s.get("era"),
             "region": s.get("region"), "macros": s.get("macros", []), "tips": s.get("tips", "")}
            for s in load_styles().values()]
