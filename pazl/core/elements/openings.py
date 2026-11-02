"""Windows, doors, arcades, niches, artwork panels. All attach to a face anchor:
local X along the face, Y outward, Z up, origin on the outer wall surface."""
from __future__ import annotations

import ast
import math

from .. import geo as g
from ..registry import P, Part, element
from .common import grid_positions, opening_shape

FILLS = ["all", "random", "checker", "alternate", "symmetric", "formula"]
_FORMULA_NODES = (ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Name, ast.Load, ast.Constant,
                  ast.Tuple, ast.List, ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
                  ast.Mod, ast.USub, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.IfExp)


def _formula(expr: str):
    """Safe arithmetic/boolean expression of c, r, cols, rows, n -> callable (no names or calls besides those)."""
    tree = ast.parse(str(expr), mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _FORMULA_NODES) or (isinstance(node, ast.Name) and node.id not in ("c", "r", "cols", "rows", "n")):
            raise ValueError(f"fill_formula: only numbers, c, r, cols, rows, n and operators are allowed: {expr!r}")
    code = compile(tree, "<fill_formula>", "eval")
    return lambda **v: bool(eval(code, {"__builtins__": {}}, v))


def fill_plan(p, ctx, pos) -> list:
    """For each grid position: True = real window, False = something else (bricked up / shutters / boards)."""
    mode = p.get("fill") or "all"
    if mode == "all":
        return [True] * len(pos)
    cols = max((c for _, _, c, _ in pos), default=0) + 1
    rows = max((r for _, _, _, r in pos), default=0) + 1
    share = float(p.get("fill_share", 0.7))
    rng = ctx.rng
    sym = {}
    out = []
    fn = _formula(p.get("fill_formula") or "True") if mode == "formula" else None
    for n, (_, _, c, r) in enumerate(pos):
        if mode == "random":
            out.append(rng.random() < share)
        elif mode == "checker":
            out.append((c + r) % 2 == 0)
        elif mode == "alternate":
            out.append(c % 2 == 0)
        elif mode == "symmetric":
            key = (min(c, cols - 1 - c), r)
            if key not in sym:
                sym[key] = rng.random() < share
            out.append(sym[key])
        else:
            out.append(fn(c=c, r=r, cols=cols, rows=rows, n=n))
    if not any(out) and out:  # never a completely blind facade by accident
        out[len(out) // 2] = True
    return out


def _blank(p, ctx, w, h, kind, part: Part, u, v, how):
    """A slot without a window: blind (bricked-up niche), closed shutters or boarded up - the wall stays closed."""
    if how == "none":
        return
    seg = ctx.seg(w / 2, 8, 40)
    shape = opening_shape(kind, w, h, seg)
    T = g.mat_t(u, 0, v)
    if how == "blind":  # shallow niche in the wall's own material + the usual surround
        part.cut(g.xf(g.prism_xz(shape, -0.06, 0.05), T))
    elif how == "shutters":
        sh = ctx.mat(p.get("shutter_material", "shutter"))
        part.add(g.xf(g.prism_xz(g.offset2(shape, 0.02), -0.02, 0.04), T), sh)
        part.add(g.xf(g.box(-0.015, 0.03, 0, 0.015, 0.06, h * 0.98), T), sh)  # the gap between the two leaves
    else:  # boarded up: dark hole behind planks
        part.cut(g.xf(g.prism_xz(shape, -0.1, 0.05), T))
        wood = ctx.mat("wood")
        boards = [g.box(-w / 2 - 0.08, -0.02, z, w / 2 + 0.08, 0.03, z + 0.16) for z in [h * k / 5 for k in range(5)]]
        part.add(g.xf(g.union(boards) ^ g.prism_xz(g.offset2(shape, 0.08), -0.05, 0.1), T), wood)
    if p.get("sill_ledge", True) and kind not in ("round", "rose", "slit"):
        part.add(g.xf(g.box(-w / 2 - 0.06, -0.02, -0.06, w / 2 + 0.06, 0.07, 0.0), T), ctx.mat(p.get("trim_material", "trim")))
    _trim(p, ctx, w, h, kind, shape, part, T, ctx.mat(p.get("trim_material", "trim")))


SHAPES = ["rect", "arch", "segmental", "lancet", "round", "rose", "horseshoe", "ogee", "slit", "ribbon", "triangle"]
TRIMS = ["none", "simple", "classic", "pediment", "segment_pediment", "baroque", "gothic_hood", "nalichnik",
         "archivolt", "rustic", "soviet"]

GRID_PARAMS = {
    "cols": P("auto", "columns: int or 'auto'"), "rows": P("auto", "rows: int or 'auto' (= floors of host)"),
    "us": P(None, "explicit u centres along the face (m or '50%')"), "vs": P(None, "explicit v bottoms"),
    "margin": P(1.0, "edge margin for auto columns"), "sill": P(None, "v of first row (default plinth+0.9)"),
    "row_step": P(None, "vertical step (default floor height)"), "skip": P(None, "[[col,row],...] to leave out"),
    "only_rows": P(None, "list of row indices to keep"), "only_cols": P(None, ""),
}


def _window(p, ctx, w, h, depth, kind, part: Part, u, v):
    """Build one window at (u, v) into part (solids + cutters)."""
    seg = ctx.seg(w / 2, 8, 40)
    shape = opening_shape(kind, w, h, seg)
    T = g.mat_t(u, 0, v)
    recess = float(p.get("recess", 0.12))
    fw = float(p.get("frame_w", 0.07))
    fd = float(p.get("frame_d", 0.08))
    frame_mat, glass_mat = ctx.mat(p.get("frame_material", "frame")), ctx.mat(p.get("glass_material", "glass"))
    trim_mat = ctx.mat(p.get("trim_material", "trim"))
    if p.get("stained"):
        glass_mat = ctx.art("stained_glass", p.get("subject") or "gothic stained glass, saints and geometric tracery")
    # opening through the wall
    part.cut(g.xf(g.prism_xz(shape, -depth - 0.05, 0.05), T))
    inner = g.offset2(shape, -fw)
    if p.get("frame", True) and not inner.is_empty():
        # frame is 3 cm bigger than the hole so it is embedded in the wall (no gaps, one solid)
        ring = g.prism_xz(g.offset2(shape, 0.03) - inner, -recess - fd, -recess)
        part.add(g.xf(ring, T), frame_mat)
        # mullions / glazing bars
        mx, my = (p.get("mullions") or [0, 0])
        bars = []
        bw = fw * 0.6
        for i in range(int(mx)):
            x = -w / 2 + w * (i + 1) / (int(mx) + 1)
            bars.append(g.box(x - bw / 2, -recess - fd * 0.8, 0, x + bw / 2, -recess - fd * 0.2, h))
        for j in range(int(my)):
            z = h * (j + 1) / (int(my) + 1)
            bars.append(g.box(-w / 2, -recess - fd * 0.8, z - bw / 2, w / 2, -recess - fd * 0.2, z + bw / 2))
        if kind == "rose" and not ctx.low:
            r = min(w, h) / 2
            for k in range(12):
                a = math.pi * 2 * k / 12
                bars.append(g.beam([math.cos(a) * r * 0.25, -recess - fd / 2, h / 2 + math.sin(a) * r * 0.25],
                                   [math.cos(a) * r, -recess - fd / 2, h / 2 + math.sin(a) * r], bw * 1.5, fd * 0.6))
            bars.append(g.rod([0, -recess - fd * 0.8, h / 2], [0, -recess - fd * 0.2, h / 2], r * 0.28, seg))
        if bars:
            part.add(g.xf(g.prism_xz(g.offset2(inner, 0.02), -recess - fd, -recess) ^ g.union(bars), T), frame_mat)
        if p.get("glazed", True):
            part.add(g.xf(g.prism_xz(g.offset2(inner, 0.02), -recess - fd * 0.55, -recess - fd * 0.45), T), glass_mat)
            if not p.get("stained") and p.get("interior", True):
                _fake_interior(part, ctx, w, h, depth, recess + fd, T)
    elif p.get("glazed", True) and not p.get("frame", True):
        part.add(g.xf(g.prism_xz(g.offset2(shape, 0.02), -recess - 0.03, -recess), T), glass_mat)
    # sill ledge
    if p.get("sill_ledge", True) and kind not in ("round", "rose", "slit"):
        part.add(g.xf(g.box(-w / 2 - 0.06, -recess - 0.02, -0.06, w / 2 + 0.06, 0.07, 0.0), T), trim_mat)
    _trim(p, ctx, w, h, kind, shape, part, T, trim_mat)
    W_face = ctx.anchor.w if ctx.anchor and ctx.anchor.kind == "face" else None
    fits = W_face is None or (u - w - 0.1 >= 0 and u + w + 0.1 <= W_face)  # open shutters need wall on both sides
    if p.get("shutters") and kind in ("rect", "arch", "segmental") and fits:
        sh_mat = ctx.mat(p.get("shutter_material", "shutter"))
        for sx in (-1, 1):
            x0 = sx * (w / 2 + 0.05)
            # 2 cm into the wall: a shutter only touching the surface would be a separate (floating) piece
            part.add(g.xf(g.box(min(x0, x0 + sx * w / 2), -0.02, 0.0, max(x0, x0 + sx * w / 2), 0.04, h * 0.98), T), sh_mat)


def _fake_interior(part, ctx, w, h, depth, behind, T):
    """Picture of a room just behind the glass (overlay layer, not welded): parallax-free '2D that looks 3D'."""
    from ..decals import interior_kind_for
    kind = ctx.style.get("_interior") or interior_kind_for(ctx.style)
    mat = f"interior_{kind}_{ctx.rng.randrange(4)}"
    y = -min(max(depth - 0.02, behind + 0.01), behind + 0.04)
    pts = [[-w / 2, y, 0.0], [w / 2, y, 0.0], [w / 2, y, h], [-w / 2, y, h]]
    part.decal([(T @ [*q, 1.0])[:3] for q in pts], mat, "interior")


def _trim(p, ctx, w, h, kind, shape, part, T, mat):
    trim = p.get("trim", "simple")
    if trim == "none" or kind == "slit":
        return
    tw = float(p.get("trim_w", 0.12))
    out = float(p.get("trim_out", 0.04))
    solids = []
    if trim in ("simple", "classic", "pediment", "segment_pediment", "baroque", "nalichnik", "archivolt", "soviet", "rustic"):
        ring = g.offset2(shape, tw) - shape
        if trim == "soviet":  # only a flat frame band
            ring = g.offset2(shape, 0.05) - shape
        solids.append(g.prism_xz(ring, -0.02, out))
    top = h + tw
    if trim in ("classic", "pediment"):
        solids.append(g.box(-w / 2 - tw * 1.6, -0.02, top, w / 2 + tw * 1.6, out * 2.5, top + 0.12))
    if trim == "pediment":
        solids.append(g.prism_xz(g.poly([(-w / 2 - tw * 1.6, 0), (w / 2 + tw * 1.6, 0), (0, w * 0.28)]), -0.02, out * 2.5)
                      .translate([0, 0, top + 0.12]))
    if trim == "segment_pediment":
        r = w / 2 + tw * 1.6
        solids.append(g.prism_xz(opening_shape("segmental", 2 * r, 0.45, 32), -0.02, out * 2.5).translate([0, 0, top]))
    if trim == "baroque":
        solids.append(g.box(-w / 2 - tw * 1.8, -0.02, top, w / 2 + tw * 1.8, out * 2.5, top + 0.1))
        solids.append(g.box(-0.12, -0.02, h - 0.15, 0.12, out * 2, top + 0.15))  # keystone
        for sx in (-1, 1):  # broken scrolls
            solids.append(g.rod([sx * (w / 2 + tw), -0.02, top + 0.25], [sx * (w / 2 + tw), out * 2.5, top + 0.25], 0.15, ctx.seg(.15, 6, 16)))
    if trim == "gothic_hood":  # drip mould following the arch
        ring = g.offset2(shape, tw * 1.4) - g.offset2(shape, tw * 0.6)
        ring = ring - g.rect2(w * 3, h * 0.6, 0, -1)
        solids.append(g.prism_xz(ring, -0.02, out * 2))
    if trim == "nalichnik":  # russian carved casing: wide boards + kokoshnik top + bottom apron
        solids.append(g.box(-w / 2 - tw * 2, -0.02, top, w / 2 + tw * 2, out * 1.5, top + 0.18))
        crest = opening_shape("ogee", w + tw * 3, w * 0.55, 32)
        solids.append(g.prism_xz(crest, -0.02, out * 1.2).translate([0, 0, top + 0.18]))
        solids.append(g.box(-w / 2 - tw * 1.5, -0.02, -0.4, w / 2 + tw * 1.5, out * 1.2, -0.06))
    if trim == "archivolt":
        ring = g.offset2(shape, tw * 2.2) - g.offset2(shape, tw)
        ring = ring - g.rect2(w * 3, max(0.01, h - w / 2), 0, -1)
        solids.append(g.prism_xz(ring, -0.02, out * 2))
    if trim == "rustic":  # voussoirs / keystone above
        solids.append(g.box(-0.14, -0.02, h - 0.05, 0.14, out * 2, top + 0.2))
    for s in solids:
        part.add(g.xf(s, T), mat)


WIN_PARAMS = {
    "kind": P("rect", "opening shape", SHAPES), "w": P(1.2, "width"), "h": P(1.5, "height"),
    **GRID_PARAMS,
    "frame": P(True, "window frame"), "frame_w": P(0.07, ""), "frame_d": P(0.08, ""),
    "mullions": P([1, 1], "[vertical bars, horizontal bars]"), "glazed": P(True, "glass (false = open arcade)"),
    "recess": P(0.12, "how deep the frame sits in the wall"), "sill_ledge": P(True, ""),
    "trim": P("simple", "surround style", TRIMS), "trim_w": P(0.12, ""), "trim_out": P(0.04, ""),
    "fill": P("all", "which grid slots get a window: all, random (share), checker, alternate (every other column), "
                     "symmetric (random but mirrored), formula", FILLS),
    "fill_share": P(0.7, "share of real windows for random/symmetric (0..1)"),
    "fill_formula": P(None, "for fill=formula: expression of c (column), r (row), cols, rows, n (index); true = window. "
                            "E.g. '(c + r) % 2 == 0', 'c in (0, cols - 1)', 'r > 0 and c % 3 != 1'"),
    "fill_other": P("mix", "what the other slots get", ["mix", "blind", "shutters", "boarded", "none"]),
    "shutters": P(False, ""), "stained": P(False, "stained glass (unique art texture slot)"),
    "subject": P(None, "stained glass subject for the texture prompt"),
    "frame_material": P("frame", ""), "glass_material": P("glass", ""), "trim_material": P("trim", ""),
    "shutter_material": P("shutter", ""),
}


@element("windows", "openings", "Grid of windows on a face. Cuts real holes through the wall, adds frame, glass, "
         "sill and surround. Use kind=arch + glazed=false + frame=false for an open arcade.",
         WIN_PARAMS, attach="face", title_ru="Окна (сетка)")
def windows(p, ctx):
    part = Part()
    depth = ctx.anchor.depth if ctx.anchor else 0.5
    w, h = float(p["w"]), float(p["h"])
    pos = grid_positions(p, ctx.anchor, w)
    other = p.get("fill_other") or "mix"
    for (u, v, c, r), real in zip(pos, fill_plan(p, ctx, pos)):
        if real:
            _window(p, ctx, w, h, depth, p["kind"], part, u, v)
        else:
            _blank(p, ctx, w, h, p["kind"], part, u, v, ctx.rng.choice(["blind", "blind", "shutters", "boarded"]) if other == "mix" else other)
    return part


@element("window", "openings", "Single window at `at`=[u, v] (u = centre along face, v = sill height).",
         {k: v for k, v in WIN_PARAMS.items() if k not in GRID_PARAMS}, attach="face", title_ru="Окно")
def window(p, ctx):
    part = Part()
    depth = ctx.anchor.depth if ctx.anchor else 0.5
    _window(p, ctx, float(p["w"]), float(p["h"]), depth, p["kind"], part, 0.0, 0.0)
    return part


@element("door", "openings", "Door / portal / gate at `at`=[u, v]. v defaults to the ground. Optional steps, canopy, "
         "transom, receding (gothic/romanesque) portal orders.",
         {"kind": P("rect", "", SHAPES), "w": P(1.2, ""), "h": P(2.3, ""), "double": P(False, "two leaves"),
          "leaf_material": P("door", ""), "recess": P(0.15, ""), "trim": P("simple", "", TRIMS), "trim_w": P(0.15, ""),
          "orders": P(0, "receding portal orders (gothic/romanesque), 0..5"), "glazed": P(False, "glass door"),
          "steps": P(0, "steps down to ground in front (count)"), "step_h": P(0.16, ""),
          "canopy": P("none", "", ["none", "slab", "gable", "arch"]), "transom": P(False, "fanlight above"),
          "trim_material": P("trim", ""), "open": P(False, "no leaf (open passage)")},
         attach="face", title_ru="Дверь / портал")
def door(p, ctx):
    part = Part()
    depth = ctx.anchor.depth if ctx.anchor else 0.5
    w, h, kind = float(p["w"]), float(p["h"]), p["kind"]
    seg = ctx.seg(w / 2, 8, 40)
    shape = opening_shape(kind, w, h, seg)
    trim_mat = ctx.mat(p["trim_material"])
    orders = int(p["orders"])
    step_o = 0.18
    # receding orders cut a stepped funnel into the wall
    for k in range(orders, 0, -1):
        sh = opening_shape(kind, w + 2 * k * step_o, h + k * step_o * (1 if kind in ("rect",) else 1.0), seg)
        part.cut(g.prism_xz(sh, -min(depth * 0.6, k * 0.15), 0.05))
        if not ctx.low:  # small colonnettes in each order
            part.add(g.cyl(0.06, h * 0.75, 8, 0, None, -(w / 2 + k * step_o), -k * 0.15 + 0.02), trim_mat)
            part.add(g.cyl(0.06, h * 0.75, 8, 0, None, (w / 2 + k * step_o), -k * 0.15 + 0.02), trim_mat)
    part.cut(g.prism_xz(shape, -depth - 0.05, 0.05))
    rec = float(p["recess"]) + orders * 0.15
    if not p["open"]:
        leaf_mat = ctx.mat("glass" if p["glazed"] else p["leaf_material"])
        part.add(g.prism_xz(g.offset2(shape, 0.03), -rec - 0.06, -rec), leaf_mat)
        if p["double"] and not ctx.low:
            part.add(g.box(-0.02, -rec + 0.0, 0, 0.02, -rec + 0.02, h * 0.95), ctx.mat("frame"))
        if not ctx.low and not p["glazed"]:  # panels relief
            for zz in (0.25, h * 0.55):
                hh = min(0.7, h * 0.3)
                for xx in ([-w / 4, w / 4] if p["double"] else [0.0]):
                    pw = w / (2 if p["double"] else 1) * 0.6
                    part.add(g.box(xx - pw / 2, -rec + 0.0, zz, xx + pw / 2, -rec + 0.025, zz + hh), leaf_mat)
    if p["transom"]:
        part.add(g.box(-w / 2, -rec - 0.08, h * 0.78, w / 2, -rec + 0.01, h * 0.8), ctx.mat("frame"))
    if p["trim"] != "none":
        _trim({"trim": p["trim"], "trim_w": p["trim_w"]}, ctx, w + orders * 2 * step_o, h + orders * step_o, kind,
              opening_shape(kind, w + orders * 2 * step_o, h + orders * step_o, seg), part, g.mat_t(), trim_mat)
    n = int(p["steps"])
    if n:
        sh = float(p["step_h"])
        for i in range(n):
            part.add(g.box(-w / 2 - 0.3 - (n - i) * 0.0, -0.05, -sh * (i + 1), w / 2 + 0.3, 0.32 * (i + 1), -sh * i), ctx.mat("stairs"))
    cz = h + 0.25
    if p["canopy"] == "slab":
        part.add(g.box(-w / 2 - 0.5, -0.1, cz, w / 2 + 0.5, 1.3, cz + 0.12), ctx.mat("trim"))
    elif p["canopy"] == "gable":
        cw = w / 2 + 0.5
        part.add(g.hull([[-cw, -0.1, cz], [cw, -0.1, cz], [0, -0.1, cz + 0.6], [-cw, 1.2, cz], [cw, 1.2, cz], [0, 1.2, cz + 0.6]]), ctx.mat("roof"))
        for sx in (-1, 1):
            part.add(g.box(sx * cw - 0.06, 1.05, -n * float(p["step_h"]), sx * cw + 0.06, 1.17, cz + 0.02), ctx.mat("wood"))
    elif p["canopy"] == "arch":
        part.add(g.prism_xz(g.offset2(opening_shape("arch", w + 1, h + 0.8, seg), 0.12) - opening_shape("arch", w + 1, h + 0.8, seg),
                            -0.05, 0.25), trim_mat)
    return part


@element("panel", "decor", "Flat artwork/plaque on a face: mosaic, fresco, painting, icon, relief, sign, clock. "
         "Gets its own unique texture slot whose prompt is `subject`.",
         {"kind": P("mosaic", "", ["mosaic", "fresco", "painting", "icon", "relief", "sign", "clock", "coat_of_arms"]),
          "subject": P("ornament", "what is depicted (used as texture prompt)"), "w": P(2.0, ""), "h": P(2.0, ""),
          "shape": P("rect", "", ["rect", "arch", "round", "lancet"]), "frame": P(True, ""), "depth": P(0.05, ""),
          "frame_material": P("trim", "")},
         attach="face", title_ru="Мозаика / фреска / икона / табличка")
def panel(p, ctx):
    w, h = float(p["w"]), float(p["h"])
    shape = opening_shape(p["shape"], w, h, ctx.seg(w / 2, 8, 48))
    art = ctx.art(p["kind"], p["subject"])
    d = float(p["depth"]) * (3 if p["kind"] == "relief" else 1)
    part = Part().add(g.prism_xz(shape, -0.02, d), art)
    if p["frame"]:
        part.add(g.prism_xz(g.offset2(shape, 0.08) - shape, -0.02, d + 0.04), ctx.mat(p["frame_material"]))
    return part


@element("niche", "decor", "Recessed niche in the wall (for statues, icons, blind arcades). Row with cols/us.",
         {"kind": P("arch", "", SHAPES), "w": P(0.8, ""), "h": P(1.8, ""), "depth": P(0.25, ""), **GRID_PARAMS,
          "trim": P("simple", "", TRIMS)},
         attach="face", title_ru="Ниша")
def niche(p, ctx):
    part = Part()
    w, h = float(p["w"]), float(p["h"])
    shape = opening_shape(p["kind"], w, h, ctx.seg(w / 2, 8, 32))
    dmax = (ctx.anchor.depth if ctx.anchor else 0.5) * 0.8
    for u, v, c, r in grid_positions({**p, "rows": p.get("rows") if p.get("rows") != "auto" else 1}, ctx.anchor, w):
        T = g.mat_t(u, 0, v)
        part.cut(g.xf(g.prism_xz(shape, -min(float(p["depth"]), dmax), 0.05), T))
        _trim(p, ctx, w, h, p["kind"], shape, part, T, ctx.mat("trim"))
    return part
