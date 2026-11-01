"""Recipe -> geometry.

Recipe element:
  {"id": "main", "type": "block", "params": {...},
   "on": "hostId:anchorName",        # optional attachment
   "at": [u, v] | [x, y] | [x,y,z],  # position in the anchor frame (numbers or "50%")
   "offset": [x, y, z], "rot": deg,  # extra local offset / rotation around local Z
   "repeat": {"count": n, "step": [dx,dy,dz], "rot": deg},
   "mirror_u": true,                 # also place the mirrored copy on the face (u -> W-u)
   "subtract": true,                 # solids cut the host instead of being added
   "cut": ["otherId", ...],          # cutters also applied to these elements
   "material": "...", "hidden": false}
"""
from __future__ import annotations

import copy
import json
import math
import traceback
from dataclasses import dataclass, field

import numpy as np

from . import geo as g
from .materials import MATS
import random

from .registry import ELEMENTS, Anchor, Ctx, Part, has_mix, pct, rand_value
from .styles import get_style

_CACHE: dict[str, Part] = {}
_CACHE_MAX = 4000


@dataclass
class ElemResult:
    id: str
    type: str
    host: str | None
    world: list = field(default_factory=list)       # instance matrices
    solids: list = field(default_factory=list)      # [(Manifold world, material)]
    anchors: dict = field(default_factory=dict)     # name -> Anchor (world)
    error: str | None = None
    notes: list = field(default_factory=list)
    src: dict = field(default_factory=dict)        # the (expanded) recipe element
    decals: list = field(default_factory=list)      # overlay quads in world coords {"pts","mat","kind"}
    info: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)      # resolved params (first instance)


@dataclass
class BuildResult:
    elements: dict
    order: list
    errors: list
    detail: str
    recipe: dict = field(default_factory=dict)
    _final: object = None

    def overlay(self, kinds=None):
        """Overlay layer quads (decals, fake interiors) - NOT part of the watertight shell."""
        return [(eid, d) for eid, r in self.elements.items() for d in r.decals if kinds is None or d["kind"] in kinds]

    def final(self):
        if self._final is None:
            solids = [m for e in self.elements.values() for m, _ in e.solids]
            self._final = g.union(solids)
        return self._final


def resolve_params(etype, given: dict, style: dict, rng=None, keep_mix=False) -> dict:
    spec = ELEMENTS[etype].params
    out = {k: copy.deepcopy(v.default) for k, v in spec.items()}
    out.update(copy.deepcopy(style.get("defaults", {}).get(etype, {})))
    out.update(copy.deepcopy(given or {}))
    if rng is not None:
        for k, v in list(out.items()):
            if isinstance(v, dict) and ("rand" in v or "choice" in v or ("mix" in v and not keep_mix)):
                out[k] = rand_value(v, rng)
    return out


_DECAL_COUNTER: list = []
INHERIT = ("style", "colors")  # keys a macro hands down to its children


def _apply_overrides(children: list, overrides: dict) -> list:
    """Macro overrides: {"childId": {"params": {...}, "at": ..., "remove": true}, "sub/child": {...}}.
    Keys for nested macros ("x/y") are handed down to child macro x."""
    if not overrides:
        return children
    out = []
    for c in children:
        c = copy.deepcopy(c)
        ov = overrides.get(c["id"], {})
        if ov.get("remove"):
            continue
        for k, v in ov.items():
            if k == "params":
                c.setdefault("params", {}).update(v)
            elif k != "remove":
                c[k] = v
        nested = {k.partition("/")[2]: v for k, v in overrides.items() if k.startswith(c["id"] + "/")}
        if nested:
            c.setdefault("overrides", {}).update(nested)
        out.append(c)
    for k, v in overrides.items():  # extra children added through overrides
        if v.get("add"):
            out.append({"id": k, **v["add"]})
    return out


def expand(elements: list, style: dict, detail: str, prefix="", parent=None, depth=0, seed=1, inherit=None) -> list:
    """Recursively expand macro elements into plain elements."""
    out = []
    inherit = inherit or {}
    ids = {e.get("id") for e in elements}
    for e in elements:
        e = copy.deepcopy(e)
        eid = prefix + e["id"]
        if prefix:
            on = e.get("on")
            if on:
                hid, _, an = on.partition(":")
                if hid in ids:
                    e["on"] = f"{prefix}{hid}:{an}"
            elif parent:
                e["on"] = f"{parent}:origin"
            e["cut"] = [prefix + c if c in ids else c for c in e.get("cut", [])]
        e["id"] = eid
        for k, v in inherit.items():
            if k == "colors":
                e["colors"] = {**v, **(e.get("colors") or {})}
            else:
                e.setdefault(k, v)
        et = ELEMENTS.get(e.get("type"))
        if et and et.macro and depth < 6:
            st = get_style(e["style"]) if e.get("style") else style
            params = resolve_params(e["type"], e.get("params"), st, random.Random(f"{seed}:{eid}"), keep_mix=True)
            ctx = Ctx(detail, None, st, MATS, eid, seed=seed)
            try:
                part = et.gen(params, ctx)
            except Exception as ex:
                out.append({**e, "type": "_group", "macro_type": e["type"], "error": f"{type(ex).__name__}: {ex}"})
                continue
            shell = {k: v for k, v in e.items() if k in ("id", "on", "at", "offset", "rot", "repeat", "hidden", "note", "style", "colors")}
            shell["type"] = "_group"
            shell["macro_type"] = e["type"]
            out.append(shell)
            sub_inherit = {k: e[k] for k in INHERIT if e.get(k)}
            out += expand(_apply_overrides(part.children, e.get("overrides") or {}), style, detail, eid + "/", eid, depth + 1,
                          seed, sub_inherit)
        else:
            out.append(e)
    return out


# element types that lay themselves out along the whole face (their own u positions): default at = face origin
FACE_LAYOUT_TYPES = {"windows", "niche", "buttresses", "balconies", "pilasters", "timber_frame", "panel_grid",
                     "curtain_wall", "colonnade"}


def _local_matrix(e: dict, anchor: Anchor | None, u_override=None) -> np.ndarray:
    at = list(e.get("at") or [])
    if anchor is not None and anchor.kind == "face":
        u0 = 0.0 if e.get("type") in FACE_LAYOUT_TYPES else anchor.w / 2
        u = pct(at[0], anchor.w) if len(at) > 0 else u0
        v = pct(at[1], anchor.h) if len(at) > 1 else 0.0
        if u_override is not None:
            u = u_override
        T = g.mat_t(u, 0, v)
    else:
        W = anchor.w if anchor else 0
        H = anchor.h if anchor else 0
        xyz = [pct(at[i], [W, H, 0][i]) if i < len(at) else 0.0 for i in range(3)]
        T = g.mat_t(*xyz)
    off = e.get("offset") or [0, 0, 0]
    T = T @ g.mat_t(*[float(x) for x in (list(off) + [0, 0, 0])[:3]])
    if e.get("rot"):
        T = T @ g.mat_rz(float(e["rot"]))
    return T


def _anchor_key(a: Anchor | None):
    if a is None:
        return None
    return [a.kind, round(a.w, 4), round(a.h, 4), round(a.depth, 4), a.floors, round(a.floor_h, 4), round(a.base, 4),
            [[round(x, 4), round(y, 4)] for x, y in (a.footprint or [])], round(a.height, 4),
            {k: v for k, v in a.extra.items() if isinstance(v, (int, float, str, bool))}]


def _register_unknown(m, mat, eid):
    oid = m.original_id()
    if oid >= 0:
        if oid not in g.REGISTRY:
            g.REGISTRY[oid] = (mat, eid)
        return
    mesh = m.to_mesh()
    for rid in set(int(x) for x in mesh.run_original_id):
        if rid not in g.REGISTRY:
            g.REGISTRY[rid] = (mat, eid)


def generate(etype, params, detail, anchor, style, eid, seed=1) -> Part:
    key = json.dumps([etype, params, detail, _anchor_key(anchor), style.get("id"), eid, seed], sort_keys=True, default=str)
    part = _CACHE.get(key)
    if part is not None:
        MATS.art.update(part.info.get("_art", {}))
        return part
    g.set_current_element(eid)
    art_before = set(MATS.art)
    ctx = Ctx(detail, anchor, style, MATS, eid, seed=seed)
    part = ELEMENTS[etype].gen(params, ctx)
    for m, mat in part.solids:
        _register_unknown(m, mat, eid)
    part.info["_art"] = {k: v for k, v in MATS.art.items() if k not in art_before}
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = part
    return part


def build(recipe: dict, detail: str | None = None) -> BuildResult:
    style = get_style(recipe.get("style", "generic"))
    detail = detail or recipe.get("detail") or style.get("detail", "realistic")
    seed = recipe.get("seed", 1)
    MATS.art.clear()
    g.PAINT.clear()
    _DECAL_COUNTER.clear()
    top_inherit = {"colors": recipe["colors"]} if recipe.get("colors") else {}
    flat = expand(recipe.get("elements", []), style, detail, seed=seed, inherit=top_inherit)
    by_id = {e["id"]: e for e in flat}
    errors = []
    # topological order by `on`
    order, state = [], {}

    def visit(eid, stack=()):
        if state.get(eid) == 2:
            return
        if state.get(eid) == 1:
            errors.append({"id": eid, "error": "circular attachment: " + " -> ".join(stack)})
            return
        state[eid] = 1
        on = by_id[eid].get("on")
        if on:
            hid = on.partition(":")[0]
            if hid in by_id:
                visit(hid, stack + (eid,))
        state[eid] = 2
        order.append(eid)

    for e in flat:
        visit(e["id"])

    res: dict[str, ElemResult] = {}
    cut_jobs = []   # (target_id, [manifold], mat, face_anchor_name)
    for eid in order:
        e = by_id[eid]
        on = e.get("on")
        host_id, anchor_name = (on.partition(":")[0], on.partition(":")[2] or "origin") if on else (None, None)
        r = ElemResult(eid, e.get("type"), host_id, src=e)
        res[eid] = r
        anchor = None
        if host_id:
            h = res.get(host_id)
            if h is None:
                r.error = f"host '{host_id}' not found"
                errors.append({"id": eid, "error": r.error})
                continue
            anchor = h.anchors.get(anchor_name)
            if anchor is None:
                r.error = f"anchor '{anchor_name}' not on '{host_id}'. Available: {sorted(h.anchors)}"
                errors.append({"id": eid, "error": r.error})
                continue
        # instances
        mats_local = []
        rep = e.get("repeat") or {}
        cnt = int(rep.get("count", 1))
        step = rep.get("step", [0, 0, 0])
        for i in range(max(1, cnt)):
            L = _local_matrix(e, anchor) @ g.mat_t(*[float(s) * i for s in (list(step) + [0, 0, 0])[:3]])
            if rep.get("rot"):
                L = L @ g.mat_rz(float(rep["rot"]) * i)
            mats_local.append(L)
            if e.get("mirror_u") and anchor is not None and anchor.kind == "face":
                at = list(e.get("at") or [anchor.w / 2])
                u = pct(at[0], anchor.w) + float(step[0]) * i
                Lm = _local_matrix(e, anchor, anchor.w - u) @ g.mat_t(0, float(step[1]) * i, float(step[2]) * i)
                mats_local.append(Lm)
        base = anchor.m if anchor is not None else np.eye(4)
        r.world = [base @ L for L in mats_local]
        if e.get("type") == "_group":
            r.anchors["origin"] = Anchor(r.world[0])
            if e.get("error"):
                r.error = e["error"]
                errors.append({"id": eid, "error": e["error"]})
            continue
        if e.get("type") not in ELEMENTS:
            r.error = f"unknown element type '{e.get('type')}'"
            errors.append({"id": eid, "error": r.error})
            continue
        est = get_style(e["style"]) if e.get("style") else style
        try:
            raw = dict(e.get("params") or {})
            if e.get("material"):
                raw["material"] = e["material"]
            params = resolve_params(e["type"], raw, est, random.Random(f"{seed}:{eid}"), keep_mix=True)
            if has_mix(params):  # {"mix":[a,b]}: every instance gets its own random value
                parts = [generate(e["type"], resolve_params(e["type"], raw, est, random.Random(f"{seed}:{eid}:{i}")),
                                  detail, anchor, est, eid, seed) for i in range(len(r.world))]
            else:
                parts = [generate(e["type"], params, detail, anchor, est, eid, seed)] * len(r.world)
            part = parts[0]
            r.params = params
        except Exception as ex:  # keep building the rest
            r.error = f"{type(ex).__name__}: {ex}"
            errors.append({"id": eid, "error": r.error, "trace": traceback.format_exc(limit=3)})
            continue
        r.info = {k: v for k, v in part.info.items() if not k.startswith("_")}
        for key, hexc in (e.get("colors") or {}).items():
            base = MATS.resolve(key, est)
            g.PAINT[(eid, base)] = f"{base}#{str(hexc).lstrip('#').lower()}"
        r.notes = part.notes
        W0 = r.world[0]
        r.anchors = {k: Anchor(W0 @ a.m, a.kind, a.w, a.h, a.depth, a.footprint, a.height, a.floors, a.floor_h, a.base, a.extra)
                     for k, a in part.anchors.items()}
        r.anchors["origin"] = Anchor(W0)
        if e.get("hidden"):
            continue
        targets = [t for t in ([host_id] if host_id else []) + list(e.get("cut", [])) if t]
        for W, part in zip(r.world, parts):
            if e.get("subtract"):
                for t in targets:
                    cut_jobs.append((t, [g.xf(m, W) for m, _ in part.solids], "@host", anchor_name))
                continue
            for m, mat in part.solids:
                r.solids.append((g.xf(m, W), mat))
            for d in part.decals:
                pts = (np.c_[np.asarray(d["pts"]), np.ones(len(d["pts"]))] @ W.T)[:, :3]
                mat = d["mat"] if d["mat"].startswith(("decal_", "interior_")) else MATS.resolve(d["mat"], est)
                n = W[:3, :3] @ np.asarray(d.get("n", [0, 1, 0]), float)
                n = n / (np.linalg.norm(n) or 1.0)
                if d["kind"] == "decal":  # every decal at its own depth (0.7 mm steps) -> overlapping decals never z-fight
                    pts = pts + n * (len(_DECAL_COUNTER) % 14) * 0.0007
                    _DECAL_COUNTER.append(1)
                r.decals.append({"pts": pts.tolist(), "n": n.tolist(), "mat": g.PAINT.get((eid, mat), mat), "kind": d["kind"]})
            if part.cutters:
                for t in targets:
                    for m, mat in part.cutters:
                        cut_jobs.append((t, [g.xf(m, W)], mat, anchor_name))
        if part.overlay:
            r.notes.append("overlay")

    # overlays on the same host face are cut by the host's face cutters too
    overlay_of = {}
    for eid, r in res.items():
        e = by_id[eid]
        if "overlay" in r.notes and r.host:
            overlay_of.setdefault((r.host, (e.get("on") or "").partition(":")[2]), []).append(eid)
    grouped: dict[str, list] = {}
    for tgt, cutters, mat, an in cut_jobs:
        grouped.setdefault(tgt, []).append((cutters, mat))
        for ov in overlay_of.get((tgt, an), []):
            grouped.setdefault(ov, []).append((cutters, mat))
    for tgt, jobs in grouped.items():
        r = res.get(tgt)
        if r is None or not r.solids:
            continue
        host_mat = r.solids[0][1]
        g.set_current_element(tgt)
        tagged = []
        for cutters, mat in jobs:
            mm = host_mat if mat == "@host" else MATS.resolve(mat, style)
            tagged += [g.tag(c, mm) for c in cutters]
        if not tagged:
            continue
        big = g.union(tagged)
        bmin, bmax = g.bbox(big)
        new = []
        for m, mat in r.solids:
            mn, mx = g.bbox(m)
            if np.all(mn <= bmax) and np.all(bmin <= mx):
                m = m - big
            new.append((m, mat))
        r.solids = new
    return BuildResult(res, order, errors, detail, recipe)
