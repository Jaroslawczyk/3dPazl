"""My elements: anything built in one project (a house, a tower top, a porch, a group of decorations ...) saved
to a shared library and inserted into any other project. One JSON per item in <DATA>/my_library/, plus a
thumbnail. Items keep their recipe (macro + overrides, or the concrete elements of a macro part), so they stay
editable after insertion."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ..paths import DATA

LIB = DATA / "my_library"
CATEGORIES = ["Здания", "Части зданий", "Окна и двери", "Крыши и купола", "Декор", "Украшения", "Природа",
              "Мебель и интерьер", "Небоскрёбы", "Другое"]
_TYPE_CAT = {"windows": "Окна и двери", "window": "Окна и двери", "door": "Окна и двери", "bay_window": "Окна и двери",
             "roof": "Крыши и купола", "dome": "Крыши и купола", "spire": "Крыши и купола", "mast": "Крыши и купола",
             "dormer": "Крыши и купола", "interior": "Мебель и интерьер", "skyscraper": "Небоскрёбы",
             "block": "Части зданий", "tower": "Части зданий", "props_cluster": "Украшения"}


_TR = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяіўąćęłńóśźż",
               ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f",
                "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya", "i", "u", "a", "c", "e", "l", "n", "o", "s", "z", "z"]))


def _slug(s):
    """Latin id from any name (element ids stay ASCII: safe in URLs, files, engines)."""
    s = "".join(_TR.get(ch, ch) for ch in str(s).strip().lower())
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:40] or "item"


def suggest_category(etype: str, macro: bool, params: dict | None = None) -> str:
    if etype == "prop":
        return "Природа" if (params or {}).get("kind") in ("tree", "bush") else "Украшения"
    if etype in _TYPE_CAT:
        return _TYPE_CAT[etype]
    if macro:
        return "Здания"
    from ..core.registry import ELEMENTS
    e = ELEMENTS.get(etype)
    return "Декор" if e is not None and e.category == "decor" else "Другое"


def collect(project, eid: str):
    """-> (elements, root_kind, root_type). A top-level element is saved as in the recipe (macro with its params and
    overrides) together with the top-level elements attached to it; a part of a macro as its concrete elements."""
    res = project.result()
    top = {e["id"]: e for e in project.recipe["elements"]}
    if eid in top:
        ids = {eid}
        changed = True
        while changed:  # top-level elements hanging on the saved one (weathering, interiors, props ...)
            changed = False
            for e in project.recipe["elements"]:
                host = str(e.get("on") or "").partition(":")[0]
                if e["id"] not in ids and (host in ids or any(host.startswith(i + "/") for i in ids)):
                    ids.add(e["id"]); changed = True
        items = [json.loads(json.dumps(top[i])) for i in [e["id"] for e in project.recipe["elements"]] if i in ids]
        root = top[eid]
        macro_type = root.get("type")
    else:
        if eid not in res.elements:
            raise KeyError(eid)
        items = []
        for x in res.order:
            if project._in_scope(x, {eid}) and res.elements[x].type != "_group":
                src = {k: v for k, v in res.elements[x].src.items() if k not in ("cut", "macro_type")}
                if res.elements[x].params and "params" not in src:
                    src["params"] = {}
                items.append(json.loads(json.dumps(src, default=str)))
        root = res.elements[eid].src
        macro_type = res.elements[eid].type
    on = str(root.get("on") or "")
    kind = "ground"
    if on:
        host, _, an = on.partition(":")
        a = res.elements.get(host).anchors.get(an or "origin") if host in res.elements else None
        kind = a.kind if a is not None and a.kind in ("face", "top") else "ground"
    return items, kind, macro_type


def save(project, eid, name="", category="", description=""):
    from ..core import geo as g
    from ..core.registry import ELEMENTS
    from ..core.render import render_sheet
    items, kind, rtype = collect(project, eid)
    if not items:
        raise ValueError(f"nothing to save in {eid}")
    LIB.mkdir(parents=True, exist_ok=True)
    name = name.strip() or eid.split("/")[-1]
    iid = _slug(name)
    k = 1
    while (LIB / f"{iid}.json").exists():
        k += 1
        iid = f"{_slug(name)}_{k}"
    res = project.result()
    sol = [m for x in res.order if project._in_scope(x, {eid}) for m, _ in res.elements[x].solids]
    size = [0, 0, 0]
    if sol:
        whole = g.union(sol)
        mn, mx = g.bbox(whole)
        size = [round(float(v), 2) for v in mx - mn]
        try:
            render_sheet(whole, LIB / f"{iid}.png", views=["iso_fl"], tile=(240, 180), title="")
        except Exception:  # a missing thumbnail must not stop saving
            pass
    root_elem = ELEMENTS.get(rtype)
    item = {"id": iid, "name": name, "description": description,
            "category": category.strip() or suggest_category(rtype, bool(root_elem and root_elem.macro), items[0].get("params")),
            "root": eid, "root_type": rtype, "attach": kind, "size": size, "style": project.recipe.get("style"),
            "source_project": project.recipe.get("name"), "created": time.strftime("%Y-%m-%d %H:%M"), "elements": items}
    (LIB / f"{iid}.json").write_text(json.dumps(item, ensure_ascii=False, indent=1), "utf-8")
    return {k: v for k, v in item.items() if k != "elements"}


def items():
    out = []
    for f in sorted(LIB.glob("*.json")):
        try:
            d = json.loads(f.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        d.pop("elements", None)
        d["thumb"] = f"/my_library/{f.stem}.png" if (LIB / f"{f.stem}.png").exists() else None
        out.append(d)
    return out


def listing():
    groups = {}
    for d in items():
        groups.setdefault(d.get("category") or "Другое", []).append(d)
    order = CATEGORIES + sorted(c for c in groups if c not in CATEGORIES)
    return {"categories": CATEGORIES, "groups": [{"category": c, "items": groups[c]} for c in order if c in groups]}


def get(iid):
    f = LIB / f"{Path(iid).name}.json"
    if not f.exists():
        raise KeyError(iid)
    return json.loads(f.read_text("utf-8"))


def update(iid, **fields):
    d = get(iid)
    for k in ("name", "category", "description"):
        if fields.get(k) is not None:
            d[k] = str(fields[k]).strip()
    (LIB / f"{d['id']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    return {k: v for k, v in d.items() if k != "elements"}


def delete(iid):
    d = get(iid)
    for ext in ("json", "png"):
        (LIB / f"{d['id']}.{ext}").unlink(missing_ok=True)
    return {"deleted": d["id"]}


def insert_ops(project, iid, on="", at=None, rot=0.0):
    """Patch ops that add a library item to the project: fresh ids, internal references rewired, the root placed on
    `on` (host:anchor) at `at`, or on the ground beside the existing model."""
    d = get(iid)
    old_root = d["root"]
    taken = {e["id"] for e in project.recipe["elements"]}
    base = _slug(d["name"])
    p, k = base, 1
    while p in taken or any(t.startswith(p + "_") for t in taken):
        k += 1
        p = f"{base}{k}"
    idmap = {}
    for e in d["elements"]:
        old = e["id"]
        # saved elements become top-level: no "/" in their ids ("/" means "inside a macro")
        idmap[old] = p if old == old_root else (f"{p}_{_slug(old[len(old_root) + 1:])}" if old.startswith(old_root + "/")
                                                else f"{p}_{_slug(old)}")

    def ref(r):
        host, sep, an = str(r).partition(":")
        if host in idmap:
            return idmap[host] + sep + an
        if host.startswith(old_root + "/"):
            return p + host[len(old_root):] + sep + an
        return r
    ops = []
    for e in d["elements"]:
        e = json.loads(json.dumps(e))
        is_root = e["id"] == old_root
        e["id"] = idmap[e["id"]]
        if is_root:
            e.pop("on", None)
            e.pop("at", None)
            if on:
                e["on"] = on
            if at is not None:
                e["at"] = list(at)
            elif not on:  # ground, beside the model
                from ..core import geo as g
                res = project.result()
                fin = res.final()
                x = 0.0
                if not fin.is_empty():
                    mn, mx = g.bbox(fin)
                    x = float(mx[0]) + 6 + float(d.get("size", [10])[0]) / 2
                e["at"] = [round(x, 2), 0.0]
            if rot:
                e["rot"] = float(rot)
        elif e.get("on"):
            e["on"] = ref(e["on"])
        if e.get("cut"):
            e["cut"] = [ref(c).partition(":")[0] for c in e["cut"]]
        ops.append({"op": "add", "element": e})
    return ops, p
