"""Vehicle kit: how a low-poly vehicle is put together, using what was measured in the CC0 packs (docs/model_craft.md).

One palette texture and one material per model. A colour is a strip of the atlas: a surface either sits at one point of
the strip (flat) or runs along it with its height (gradient, the cheap baked shading on ~3/4 of the faces of the reference
models). Stripes and lamps are painted by cutting the surface itself (`paint`), so nothing floats or flickers. Small things
are separate tiny solids. Text and patterns live in atlas cells on thin plates (`decal`). Working axes: X forward, Y left,
Z up, metres; the GLB is Y up, facing +Z, wheels and rotors are separate nodes turning around their own pivot."""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

import manifold3d
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

from .. import geo

PALETTE = {
    "paint": "#c8342c", "paint2": "#eef0f4", "white": "#eef0f4", "black": "#24262c", "dark": "#3f4250", "tyre": "#2d2e34",
    "steel": "#8f97ad", "chrome": "#ccd3df", "glass": "#a4d4e8", "glass_dark": "#4d6a7a", "lamp": "#fff1bd", "tail": "#d8282c",
    "amber": "#ffa62b", "red": "#d9483b", "orange": "#f0683a", "yellow": "#f8c13a", "green": "#3fae78", "blue": "#4f78c9",
    "sky": "#bcd6f5", "wood": "#b9714a", "wood_dark": "#8a5238", "canvas": "#ece3cd", "rust": "#a4552f", "hull_red": "#b5382f",
    "gold": "#e8b33c", "seat": "#5a4a44", "lit": "#ffd98a", "teal": "#2f8f8a",
}
SLOTS = {name: i for i, name in enumerate(PALETTE)}
ATLAS, STRIP, BAND, CELL_W, CELL_H = 512, 16, 128, 256, 64
FLAT_T = 0.72  # where on a strip a flat surface sits: this point is the colour itself


def _rgb(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], float)


def _font(size):
    for f in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _text(d, box, text, fill):
    x0, y0, x1, y1 = box
    size = y1 - y0
    while size > 8 and d.textlength(text, font=_font(size)) > (x1 - x0) * 0.94:
        size -= 2
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), text, font=_font(size), fill=fill, anchor="mm")


def draw_cell(im, spec, box, colors):
    """One atlas cell: 'plate:A123BC', 'text:ТАКСИ', 'sign:12 ЦЕНТР', 'number:7', 'checker', 'hazard', 'vent'."""
    kind, _, text = spec.partition(":")
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if kind == "plate":
        d.rectangle(box, fill="#f4f5f7")
        d.rectangle((x0 + 2, y0 + 2, x1 - 3, y1 - 3), outline="#22242a", width=3)
        _text(d, (x0 + 8, y0 + 6, x1 - 8, y1 - 6), text, "#22242a")
    elif kind == "text":
        d.rectangle(box, fill=colors["paint"])
        _text(d, (x0 + 4, y0 + 6, x1 - 4, y1 - 6), text, "#ffffff")
    elif kind == "sign":
        d.rectangle(box, fill="#17181c")
        _text(d, (x0 + 6, y0 + 8, x1 - 6, y1 - 8), text, "#ffb63a")
    elif kind == "number":
        d.rectangle(box, fill="#f4f5f7")
        _text(d, (x0 + 4, y0 + 2, x1 - 4, y1 - 2), text, "#22242a")
    elif kind == "checker":
        q = h // 2
        for i in range(w // q):
            for j in (0, 1):
                d.rectangle((x0 + i * q, y0 + j * q, x0 + (i + 1) * q - 1, y0 + (j + 1) * q - 1), fill="#17181c" if (i + j) % 2 else "#f7cf3f")
    elif kind == "hazard":
        tile = Image.new("RGB", (w + 2 * h, h), "#f8c13a")
        g = ImageDraw.Draw(tile)
        for i in range(0, w + 2 * h, 48):
            g.polygon([(i, h), (i + 24, h), (i + 24 + h, 0), (i + h, 0)], fill="#24262c")
        im.paste(tile.crop((h, 0, h + w, h)), (x0, y0))
    elif kind == "vent":
        d.rectangle(box, fill="#3f4250")
        for y in range(y0 + 6, y1 - 4, 10):
            d.rectangle((x0 + 6, y, x1 - 6, y + 4), fill="#17181c")
    else:
        raise KeyError(spec)


def _cell_box(i):
    x, y = (i % 2) * CELL_W, BAND + (i // 2) * CELL_H
    return x, y, x + CELL_W - 1, y + CELL_H - 1


def atlas(colors: dict, cells: list[str]) -> Image.Image:
    """Palette strips on top (the bottom of a strip is the shaded end), decal cells below."""
    a = np.zeros((BAND, ATLAS, 3), float)
    t = np.linspace(1, 0, BAND)[:, None]
    for name, slot in SLOTS.items():
        c = _rgb(colors.get(name) or PALETTE[name])
        low = c * 0.62 + np.array([10, 10, 22])  # shade goes cooler, not just darker
        high = np.minimum(c * 1.09 + 6, 255)
        col = np.where(t > FLAT_T, c + (high - c) * (t - FLAT_T) / (1 - FLAT_T), low + (c - low) * t / FLAT_T)
        a[:, slot * STRIP:(slot + 1) * STRIP] = col[:, None, :]
    im = Image.new("RGB", (ATLAS, ATLAS), "#808080")
    im.paste(Image.fromarray(a.clip(0, 255).astype("uint8")), (0, 0))
    full = {**PALETTE, **{k: v for k, v in colors.items() if v}}
    for i, spec in enumerate(cells):
        draw_cell(im, spec, _cell_box(i), full)
    return im


@dataclass
class Piece:
    V: np.ndarray
    F: np.ndarray
    col: str
    grad: bool
    g0: float
    g1: float
    node: str = "body"
    uv: np.ndarray | None = None


def _half(V, F, n, o):
    """The part of a triangle soup on the +n side of a plane, split exactly along it and left open (no cap)."""
    if not len(F):
        return V[:0], F[:0]
    r = trimesh.intersections.slice_faces_plane(V, F, np.asarray(n, float), np.asarray(o, float))
    return (r[0], r[1]) if len(r[1]) else (V[:0], F[:0])


def _loops(F):
    """Outlines of a coplanar patch: directed edges used once, walked into closed loops of vertex ids."""
    edges = {(int(a), int(b)) for t in F for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0]))}
    nxt: dict[int, list[int]] = {}
    for a, b in edges:
        if (b, a) not in edges:
            nxt.setdefault(a, []).append(b)
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop, v = [start], nxt[start].pop()
        if not nxt[start]:
            del nxt[start]
        while v != start:
            loop.append(v)
            w = nxt[v].pop()
            if not nxt[v]:
                del nxt[v]
            v = w
        loops.append(loop)
    return loops


def merge_coplanar(V, F):
    """Rebuild every flat patch of a surface from its outline: `paint` cuts leave slivers on big faces, and the shape,
    the colour and the gradient (linear in height) stay exactly the same without them."""
    _, first, inv = np.unique(np.round(V, 5), axis=0, return_index=True, return_inverse=True)
    W, F = V[first], inv.reshape(-1)[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    T = W[F]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    ln = np.linalg.norm(n, axis=1)
    F, T, n, ln = F[ln > 1e-10], T[ln > 1e-10], n[ln > 1e-10], ln[ln > 1e-10]
    n = n / ln[:, None]
    key = np.c_[np.round(n, 3), np.round((n * T[:, 0]).sum(1), 3)]
    _, gid = np.unique(key, axis=0, return_inverse=True)
    gid = gid.reshape(-1)
    out = []
    for g in range(gid.max() + 1 if len(gid) else 0):
        idx = np.flatnonzero(gid == g)
        Fg = F[idx]
        if len(Fg) < 3:
            out.append(Fg)
            continue
        try:
            nn = n[idx[0]]
            u = np.cross(nn, [1.0, 0, 0] if abs(nn[0]) < 0.9 else [0, 1.0, 0])
            u /= np.linalg.norm(u)
            v = np.cross(nn, u)
            flat, ids = [], []
            for loop in _loops(Fg):
                P = W[loop]
                turn = np.linalg.norm(np.cross(P - np.roll(P, 1, 0), np.roll(P, -1, 0) - P), axis=1)
                keep = turn > 1e-9  # straight runs lose their extra points
                if keep.sum() < 3:
                    continue
                flat.append(np.c_[P[keep] @ u, P[keep] @ v])
                ids += list(np.array(loop)[keep])
            ids = np.array(ids)
            G = ids[np.asarray(manifold3d.triangulate(flat)).reshape(-1, 3)]
            area = lambda A: np.linalg.norm(np.cross(W[A[:, 1]] - W[A[:, 0]], W[A[:, 2]] - W[A[:, 0]]), axis=1).sum()  # noqa: E731
            ok = abs(area(G) - area(Fg)) < 1e-6 + 1e-4 * area(Fg) and len(G) <= len(Fg)
            d = np.cross(W[G[:, 1]] - W[G[:, 0]], W[G[:, 2]] - W[G[:, 0]]) @ nn
            out.append(np.where(d[:, None] < 0, G[:, ::-1], G) if ok else Fg)
        except (KeyError, IndexError, RuntimeError, ValueError):
            out.append(Fg)  # an outline that touches itself: leave this patch as it is
    return W, (np.vstack(out) if out else F)


class Kit:
    def __init__(self, p: dict, R):
        self.p, self.R = p, R
        self.d = int(p["detail"])
        self.seg = {1: 8, 2: 8, 3: 12}[self.d]
        self.pieces: list[Piece] = []
        self.pivots: dict[str, tuple] = {}
        self.cells: list[str] = []
        self.colors = {"paint": p.get("color") or "", "paint2": p.get("color2") or ""}

    def default_colors(self, paint, paint2=""):
        self.colors["paint"] = self.colors["paint"] or paint
        self.colors["paint2"] = self.colors["paint2"] or paint2

    def add(self, m, col, grad=True, node="body") -> Piece:
        mesh = m.to_mesh()
        V = np.asarray(mesh.vert_properties)[:, :3].astype(float)
        p = Piece(V, np.asarray(mesh.tri_verts).astype(np.int64), col, grad, float(V[:, 2].min()), float(V[:, 2].max()), node)
        self.pieces.append(p)
        return p

    def add_raw(self, V, F, col, grad=True, node="body") -> Piece:
        """A hand-made surface, for shapes that do not need closed solids."""
        p = Piece(np.asarray(V, float), np.asarray(F, np.int64), col, grad, float(V[:, 2].min()), float(V[:, 2].max()), node)
        self.pieces.append(p)
        return p

    def stud(self, x, y, z, r, s, col="chrome", top="dark", seg=6):
        """Round fitting on a side wall (s = +1 or -1 along Y): a sloped rim and a flat centre, 16 triangles."""
        a = np.arange(seg) * 2 * np.pi / seg
        ring = lambda rr, h: np.c_[x + rr * np.cos(a), np.full(seg, y + s * h), z + rr * np.sin(a)]  # noqa: E731
        i, j = np.arange(seg), (np.arange(seg) + 1) % seg
        F = np.vstack([np.c_[i, i + seg, j + seg], np.c_[i, j + seg, j]])
        fan = np.c_[np.zeros(seg - 2, int), np.arange(2, seg), np.arange(1, seg - 1)]
        flip = (lambda f: f) if s > 0 else (lambda f: f[:, ::-1])
        self.add_raw(np.vstack([ring(r, -0.06), ring(r * 0.72, 0.02)]), flip(F), col, False)
        self.add_raw(ring(r * 0.72, 0.02), flip(fan), top, False)

    def paint(self, p: Piece, col, x=None, y=None, z=None, grad=None, planes=()) -> Piece:
        """Recolour what lies inside a box and/or half-spaces (n, o): the surface is cut, the shape does not change."""
        cuts = list(planes)
        for i, rng in enumerate((x, y, z)):
            if rng:
                e = np.eye(3)[i]
                if rng[0] is not None:
                    cuts.append((e, e * rng[0]))
                if rng[1] is not None:
                    cuts.append((-e, e * rng[1]))
        lo = np.array([r[0] if r and r[0] is not None else -np.inf for r in (x, y, z)])
        hi = np.array([r[1] if r and r[1] is not None else np.inf for r in (x, y, z)])
        T = p.V[p.F]
        near = ((T.max(1) >= lo) & (T.min(1) <= hi)).all(1)  # only triangles at the region are cut: a far-reaching plane would split the whole body
        V, F = p.V, p.F[near]
        rest = [(p.V, p.F[~near])]
        for n, o in cuts:
            rest.append(_half(V, F, -np.asarray(n, float), o))
            V, F = _half(V, F, n, o)
        off, Vs, Fs = 0, [], []
        for v, f in rest:
            Vs.append(v)
            Fs.append(f + off)
            off += len(v)
        p.V, p.F = np.vstack(Vs), np.vstack(Fs)
        q = Piece(V, F, col, p.grad if grad is None else grad, p.g0, p.g1, p.node)
        self.pieces.append(q)
        return q

    def bands(self, p: Piece, cuts):
        """Horizontal stripes: cuts = [(z_top, colour), ...] from the bottom up."""
        z0 = None
        for zt, col in cuts:
            self.paint(p, col, z=(z0, zt))
            z0 = zt

    def cell(self, spec: str) -> int:
        if spec not in self.cells:
            if len(self.cells) >= 12:
                raise ValueError("no free decal cells")
            self.cells.append(spec)
        return self.cells.index(spec)

    def decal(self, spec, pos, n, w, h, t=0.012, edge="dark", up=(0, 0, 1)):
        """Thin plate with a picture on its face: pos = centre of the face, n = outward direction, w x h in metres."""
        n, up, o = np.asarray(n, float), np.asarray(up, float), np.asarray(pos, float)
        r = np.cross(up, n) * w / 2
        u = up * h / 2
        face = np.array([o - r - u, o + r - u, o + r + u, o - r + u])
        back = face - n * (t + 0.02)
        x0, y0, x1, y1 = _cell_box(self.cell(spec))
        px = np.array([[x0 + 1, y1], [x1, y1], [x1, y0 + 1], [x0 + 1, y0 + 1]], float)
        uv = np.c_[px[:, 0] / ATLAS, 1 - px[:, 1] / ATLAS]
        self.pieces.append(Piece(face, np.array([[0, 1, 2], [0, 2, 3]]), "white", False, 0, 1, uv=uv))
        V = np.vstack([back, face])
        F = []
        for i in range(4):
            j = (i + 1) % 4
            F += [[i, j, j + 4], [i, j + 4, i + 4]]
        self.pieces.append(Piece(V, np.array(F), edge, False, 0, 1))

    def wheel(self, x, y, r, w, name, hub="steel", rim=0.6, lugs=0, nuts=True):
        """Tyre and hub as one spinning node, ~60 triangles like the reference wheels: built by hand, no faces inside it.
        The hub side looks away from the centre line."""
        seg = self.seg
        a = np.arange(seg) * 2 * np.pi / seg
        ring = lambda rr, z: np.c_[rr * np.cos(a), rr * np.sin(a), np.full(seg, z)]  # noqa: E731
        i, j = np.arange(seg), (np.arange(seg) + 1) % seg
        tv = np.vstack([ring(r, -w / 2), ring(r, w * 0.25), ring(r * (rim + 0.07), w / 2), ring(r * rim, w * 0.3)])
        tf = []
        for k in range(3):
            A, B, C, D = k * seg + i, k * seg + j, (k + 1) * seg + j, (k + 1) * seg + i
            tf += [np.c_[A, B, C], np.c_[A, C, D]]
        tf.append(np.c_[np.zeros(seg - 2, int), np.arange(2, seg), np.arange(1, seg - 1)])  # inner side
        hv = np.vstack([ring(r * rim, w * 0.3), [[0, 0, w * 0.42]]])
        hf = np.c_[i, j, np.full(seg, seg)]
        turn = (lambda P: np.c_[P[:, 0], P[:, 2], -P[:, 1]]) if y >= 0 else (lambda P: np.c_[P[:, 0], -P[:, 2], P[:, 1]])
        at = lambda P: turn(P) + (x, y, r)  # noqa: E731
        self.pivots[name] = (x, y, r)
        self.add_raw(at(tv), np.vstack(tf), "tyre", node=name)
        self.add_raw(at(hv), hf, hub, node=name)
        put = lambda m: m.rotate([-90 if y >= 0 else 90, 0, 0]).translate([x, y, r])  # noqa: E731
        if lugs and self.d >= 2:
            tread = [geo.box(r * 0.93, -r * 0.09, -w / 2 if n % 2 else 0, r * 1.06, r * 0.09, 0 if n % 2 else w / 2).rotate([0, 0, 360 * n / lugs]) for n in range(lugs)]
            self.add(put(geo.union(tread)), "tyre", node=name)
        if self.d >= 3 and nuts:
            bolts = [geo.cyl(r * 0.04, w * 0.1, 4, w * 0.3, cx=r * rim * 0.62 * np.cos(t), cy=r * rim * 0.62 * np.sin(t)) for t in 6.283 * (np.arange(4) + 0.5) / 4]
            self.add(put(geo.union(bolts)), "dark", False, node=name)

    # ---------------------------------------------------------------- mesh out
    def bake(self):
        """{node: (V, F, N, UV)}: one normal per face (flat shading), vertices merged again where everything matches."""
        out = {}
        for p in self.pieces:
            if not len(p.F):
                continue
            T = p.V[p.F]
            n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
            ln = np.linalg.norm(n, axis=1)
            keep = ln > 1e-9
            T, n, ln = T[keep], n[keep], ln[keep]
            if p.uv is not None:
                uv = p.uv[p.F][keep]
            else:
                u = (SLOTS[p.col] + 0.5) * STRIP / ATLAS
                t = np.clip((T[..., 2] - p.g0) / (p.g1 - p.g0), 0, 1) if p.grad and p.g1 - p.g0 > 1e-6 else np.full(T.shape[:2], FLAT_T)
                v = 1 - (1 - t) * (BAND - 4) / ATLAS - 2 / ATLAS
                uv = np.stack([np.full_like(v, u), v], axis=-1)
            N = np.repeat((n / ln[:, None])[:, None, :], 3, axis=1)
            out.setdefault(p.node, []).append((T.reshape(-1, 3), N.reshape(-1, 3), uv.reshape(-1, 2)))
        res = {}
        for node, chunks in out.items():
            V, N, UV = (np.vstack([c[i] for c in chunks]) for i in range(3))
            key = np.round(np.c_[V * 1e4, N * 1e3, UV * 1e4]).astype(np.int64)
            _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
            res[node] = (V[first], inv.reshape(-1, 3), N[first], UV[first])
        return res

    def bounds(self):
        V = np.vstack([p.V[np.unique(p.F)] for p in self.pieces if len(p.F)])
        return V.min(0), V.max(0)

    def finish(self, scale=1.0):
        """Scale and put the origin at the bottom centre."""
        lo, hi = self.bounds()
        c = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
        for p in self.pieces:
            if p.uv is None and len(p.F):
                p.V, p.F = merge_coplanar(p.V, p.F)
            p.V = (p.V - c) * scale
            p.g0, p.g1 = (p.g0 - c[2]) * scale, (p.g1 - c[2]) * scale
        self.pivots = {k: tuple((np.array(v) - c) * scale) for k, v in self.pivots.items()}

    def write(self, path: Path) -> dict:
        from trimesh.visual.material import PBRMaterial
        mat = PBRMaterial(name="palette", baseColorTexture=atlas(self.colors, self.cells), metallicFactor=0.0, roughnessFactor=0.75)
        to_gltf = lambda a: np.asarray(a)[..., [1, 2, 0]]  # noqa: E731  X forward, Y left, Z up -> Z forward, X left, Y up
        scene = trimesh.Scene()
        tris = 0
        for node, (V, F, N, UV) in self.bake().items():
            piv = np.array(self.pivots.get(node, (0, 0, 0)), float)
            m = trimesh.Trimesh(to_gltf(V - piv), F, vertex_normals=to_gltf(N), process=False)
            m.visual = trimesh.visual.TextureVisuals(uv=UV, material=mat)
            T = np.eye(4)
            T[:3, 3] = to_gltf(piv)
            scene.add_geometry(m, node_name=node, geom_name=node, transform=T)
            tris += len(F)
        path.parent.mkdir(parents=True, exist_ok=True)
        scene.export(path)
        return {"tris": tris, "nodes": ["body"] + sorted(self.pivots), "decals": list(self.cells)}


# ------------------------------------------------------------------ shape helpers
def chamfer(pts, d):
    """Cut every corner of a polygon by d (or one d per corner): the reference models have almost no bare corners."""
    n = len(pts)
    ds = d if isinstance(d, (list, tuple)) else [d] * n
    out = []
    for i, p in enumerate(pts):
        p = np.array(p, float)
        if ds[i] <= 0:
            out.append(tuple(p))
            continue
        for q in (pts[i - 1], pts[(i + 1) % n]):
            v = np.array(q, float) - p
            ln = np.linalg.norm(v)
            out.append(tuple(p + v / ln * min(ds[i], ln * 0.45)))
    return out


def rect(w, d, c=0.0, cx=0.0, cy=0.0):
    pts = [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)]
    return chamfer(pts, c) if c else pts


def side(pts, w, y=0.0):
    """Side-view polygon (x, z) pushed across the width."""
    return geo.prism_xz(geo.poly(pts), y - w / 2, y + w / 2)


def front(pts, x0, x1):
    """Front-view polygon (y, z) pushed along the length."""
    return geo.prism_yz(geo.poly(pts), x0, x1)


def plan(pts, z0, z1):
    """Top-view polygon (x, y) pushed up."""
    return geo.extrude(geo.poly(pts), z1 - z0, z0)


def block(x0, x1, y0, y1, z0, z1, c=0.0):
    """Box, with its vertical corners cut when c > 0."""
    return plan(rect(x1 - x0, y1 - y0, c, (x0 + x1) / 2, (y0 + y1) / 2), z0, z1) if c else geo.box(x0, y0, z0, x1, y1, z1)


def cylx(r, x0, x1, y=0.0, z=0.0, seg=12, r2=None):
    return geo.cyl(r, x1 - x0, seg, r2=r2).rotate([0, 90, 0]).translate([x0, y, z])


def cyly(r, y0, y1, x=0.0, z=0.0, seg=12):
    return geo.cyl(r, y1 - y0, seg).rotate([-90, 0, 0]).translate([x, y0, z])


def ring(r, t, h, seg=12, z0=0.0, x=0.0, y=0.0):
    """Open tube: the top of a funnel or a stack shows its dark inside."""
    return geo.subtract(geo.cyl(r, h, seg, z0, cx=x, cy=y), [geo.cyl(r - t, h, seg, z0 + h * 0.3, cx=x, cy=y)])


def loft(sections):
    """Body through convex sections [(x, [(y, z), ...]), ...]: fuselages."""
    return geo.union([geo.hull([(x0, y, z) for y, z in a] + [(x1, y, z) for y, z in b]) for (x0, a), (x1, b) in zip(sections, sections[1:])])


def oct_section(w, h, zc=0.0, c=0.3):
    """Eight-sided section w x h around height zc."""
    a, b = w / 2, h / 2
    return [(-a, zc - b * (1 - c)), (-a * (1 - c), zc - b), (a * (1 - c), zc - b), (a, zc - b * (1 - c)),
            (a, zc + b * (1 - c)), (a * (1 - c), zc + b), (-a * (1 - c), zc + b), (-a, zc + b * (1 - c))]
