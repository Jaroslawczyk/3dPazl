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
        for vid, v in (data.get("variants") or {}).items():  # sub-styles: parent + overrides, id "parent_variant"
            child = {k: val for k, val in data.items() if k != "variants"}
            child.update({k: val for k, val in v.items() if k not in ("materials", "defaults")})
            child["materials"] = {**data.get("materials", {}), **v.get("materials", {})}
            child["defaults"] = {et: {**data.get("defaults", {}).get(et, {}), **v.get("defaults", {}).get(et, {})}
                                 for et in {*data.get("defaults", {}), *v.get("defaults", {})}}
            child["id"], child["parent"] = f"{data['id']}_{vid}", data["id"]
            _STYLES[child["id"]] = child
    _STYLES.setdefault("generic", {"id": "generic", "name": "Generic", "materials": {}, "defaults": {}})
    return _STYLES


def get_style(sid) -> dict:
    """A style id, or a mix: "gothic+russian_orthodox" / ["gothic", "baroque"]. In a mix the first style wins for
    materials and element defaults; the others fill what it lacks (e.g. gothic walls with onion domes)."""
    s = load_styles()
    if isinstance(sid, (list, tuple)):
        sid = "+".join(sid)
    if not sid or "+" not in str(sid):
        return s.get(sid) or s["generic"]
    if sid in _MIXED:
        return _MIXED[sid]
    parts = [s[p] for p in str(sid).split("+") if p in s] or [s["generic"]]
    mixed = {"id": sid, "name": " + ".join(p.get("name", p["id"]) for p in parts),
             "name_ru": " + ".join(p.get("name_ru", p["id"]) for p in parts), "materials": {}, "defaults": {},
             "macros": [m for p in parts for m in p.get("macros", [])], "mix_of": [p["id"] for p in parts]}
    for p in reversed(parts):
        mixed["materials"].update(p.get("materials", {}))
        for et, d in p.get("defaults", {}).items():
            mixed["defaults"][et] = {**mixed["defaults"].get(et, {}), **d}
    _MIXED[sid] = mixed
    return mixed


_MIXED: dict[str, dict] = {}

# coarse periods for library filters (years, negative = BC)
PERIODS = [("ancient", "Древность", -4000, 500), ("medieval", "Средневековье", 500, 1500),
           ("early_modern", "Новое время", 1500, 1800), ("c19", "XIX век", 1800, 1900),
           ("c20", "XX век", 1900, 2000), ("contemporary", "Современность", 2000, 2100)]
REGIONS = {"europe_west": "Западная Европа", "europe_north": "Северная Европа", "europe_east": "Восточная Европа",
           "russia": "Россия / СССР", "mediterranean": "Средиземноморье", "caucasus": "Кавказ",
           "middle_east": "Ближний Восток", "north_africa": "Северная Африка", "central_asia": "Центральная Азия",
           "south_asia": "Южная Азия", "east_asia": "Восточная Азия", "americas": "Америка", "global": "Весь мир",
           "games": "Игры"}


def summary() -> list[dict]:
    return [{"id": s["id"], "name": s.get("name"), "name_ru": s.get("name_ru"), "era": s.get("era"),
             "region": s.get("region"), "years": s.get("years"), "regions": s.get("regions", []),
             "periods": periods_of(s), "macros": s.get("macros", []), "tips": s.get("tips", ""),
             "palette": s.get("palette"), "parent": s.get("parent"), "detail": s.get("detail")}
            for s in load_styles().values()]


def periods_of(s) -> list[str]:
    y = s.get("years")
    if not y:
        return [p[0] for p in PERIODS]
    return [pid for pid, _, a, b in PERIODS if y[0] < b and y[1] > a]
