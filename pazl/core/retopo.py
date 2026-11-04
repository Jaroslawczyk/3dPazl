"""Rebuild a reference model with our own topology and UVs, keeping its look ("1 к 1" without copying its mesh):
shrinkwrap - a primitive (icosphere around the part) pulled onto the reference surface;
cards      - tiny pieces (hair strands, toes) become flat 4-triangle pyramids along their main axis;
unwrap     - our own UV atlas (xatlas);
bake       - the reference textures are projected onto that atlas (closest reference point with a matching normal).
Reference surfaces are sampled densely into a k-d tree, so no rtree/embree is needed."""
from __future__ import annotations

import numpy as np
import trimesh
from PIL import Image, ImageFilter
from scipy.spatial import cKDTree


class Sampler:
    """Dense samples of a textured reference mesh: position, face normal, UV (glTF convention, v down)."""

    def __init__(self, mesh: trimesh.Trimesh, uv=None, image=None, count=400000, seed=1):
        P, fi = trimesh.sample.sample_surface(mesh, count, seed=seed)
        self.P, self.N, self.fi = np.asarray(P), np.asarray(mesh.face_normals)[fi], np.asarray(fi)
        self.tris, self.fuv = np.asarray(mesh.triangles), None
        self.tree = cKDTree(self.P)
        self.img = None
        if uv is not None and image is not None:
            tri = np.asarray(mesh.vertices)[mesh.faces[fi]]
            bc = trimesh.triangles.points_to_barycentric(tri, self.P)
            t = np.asarray(uv)[mesh.faces[fi]]
            self.uv = (t * bc[:, :, None]).sum(1)
            self.fuv = np.asarray(uv)[mesh.faces]
            self.img = np.asarray(image.convert("RGBA"), np.float32) / 255

    def closest(self, X, Nx=None, k=8):
        """Index of the nearest sample per point; with normals, the nearest one facing the same way."""
        d, i = self.tree.query(X, k=k)
        if Nx is None:
            return i[:, 0]
        ok = (self.N[i] * Nx[:, None]).sum(2) > .2
        first = np.where(ok.any(1), ok.argmax(1), 0)
        return i[np.arange(len(X)), first]

    def project(self, X, Nx=None, k=8):
        """Exact closest point on the reference triangles near each point (faces facing the same way when normals are
        given): (points, face index, barycentric)."""
        d, i = self.tree.query(X, k=k)
        cand = self.fi[i]  # (n, k) faces
        P = trimesh.triangles.closest_point(self.tris[cand.ravel()], np.repeat(X, k, 0)).reshape(len(X), k, 3)
        dist = np.linalg.norm(P - X[:, None], axis=2)
        if Nx is not None:
            fn = self.N[i]
            dist = dist + (np.einsum("nkc,nc->nk", fn, Nx) < .2) * 1e3
        j = dist.argmin(1)
        r = np.arange(len(X))
        pts, f = P[r, j], cand[r, j]
        return pts, f, trimesh.triangles.points_to_barycentric(self.tris[f], pts)

    def color_at(self, f, bc):
        """Texture colour at exact surface points (face, barycentric)."""
        uv = (self.fuv[f] * bc[:, :, None]).sum(1)
        return self._lookup(uv)

    def _lookup(self, uv):
        h, w = self.img.shape[:2]
        u, v = uv[:, 0] % 1 * (w - 1), (1 - uv[:, 1] % 1) * (h - 1)
        x0, y0 = np.floor(u).astype(int), np.floor(v).astype(int)
        x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
        fx, fy = (u - x0)[:, None], (v - y0)[:, None]
        I = self.img
        return (I[y0, x0] * (1 - fx) + I[y0, x1] * fx) * (1 - fy) + (I[y1, x0] * (1 - fx) + I[y1, x1] * fx) * fy

    def color(self, idx):
        """Bilinear texture colour at the samples (trimesh UV: v up, so the row is 1 - v)."""
        h, w = self.img.shape[:2]
        u, v = self.uv[idx, 0] % 1 * (w - 1), (1 - self.uv[idx, 1] % 1) * (h - 1)
        x0, y0 = np.floor(u).astype(int), np.floor(v).astype(int)
        x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
        fx, fy = (u - x0)[:, None], (v - y0)[:, None]
        I = self.img
        return (I[y0, x0] * (1 - fx) + I[y0, x1] * fx) * (1 - fy) + (I[y1, x0] * (1 - fx) + I[y1, x1] * fx) * fy


def grid_box(n):
    """Closed unit box [-1, 1]^3 with n = (nx, ny, nz) quads per side, outward winding."""
    Vs, Fs, off = [], [], 0
    for ax in range(3):
        a, b = [i for i in range(3) if i != ax]
        for sgn in (1, -1):
            A, B = np.meshgrid(np.linspace(-1, 1, n[a] + 1), np.linspace(-1, 1, n[b] + 1), indexing="ij")
            q = np.zeros((A.size, 3))
            q[:, a], q[:, b], q[:, ax] = A.ravel(), B.ravel(), sgn
            i = np.arange(A.size).reshape(A.shape)
            Fs.append(np.vstack([np.stack([i[:-1, :-1], i[1:, :-1], i[1:, 1:]], -1).reshape(-1, 3),
                                 np.stack([i[:-1, :-1], i[1:, 1:], i[:-1, 1:]], -1).reshape(-1, 3)]) + off)
            Vs.append(q)
            off += len(q)
    m = trimesh.Trimesh(np.vstack(Vs), np.vstack(Fs), process=False)
    m.merge_vertices()
    m.fix_normals()
    return m


def shrinkwrap(part: trimesh.Trimesh, sub=2, grow=1.6, iters=3, sampler=None, box=None):
    """A primitive around the part's oriented box pulled onto its surface. box = quads along the longest side: a grid box
    (keeps blocks crisp); otherwise an icosphere (round things) with light smoothing between pulls."""
    T, ext = trimesh.bounds.oriented_bounds(part)
    s = sampler or Sampler(part, count=max(20000, len(part.faces) * 400))
    if box:
        n = np.clip(np.round(ext / ext.max() * box), 1, box).astype(int)
        m = grid_box(n)
        m.vertices = m.vertices * ext / 2 * grow
        iters = 1
    else:
        m = trimesh.creation.icosphere(subdivisions=sub)
        m.vertices = m.vertices * ext / 2 * grow
    base = np.asarray(m.vertices) / grow if box else None  # the same grid lying on the oriented box itself
    m.apply_transform(np.linalg.inv(T))
    V = np.asarray(m.vertices)
    for it in range(iters):
        V = s.project(V)[0]
        if it < iters - 1:
            nb = [[] for _ in range(len(V))]
            for a, b in m.edges_unique:
                nb[a].append(b), nb[b].append(a)
            V = np.array([.5 * V[i] + .5 * V[n].mean(0) for i, n in enumerate(nb)])
    if box:  # an open side (shirt hem, trouser top) has no surface nearby: keep a flat cap on the box face instead of a funnel
        G = trimesh.transform_points(base, np.linalg.inv(T))
        far = np.linalg.norm(V - G, axis=1) > .15 * ext.min()
        V[far] = G[far]
    out = trimesh.Trimesh(V, m.faces, process=False)
    if np.linalg.det(T[:3, :3]) < 0:  # a mirrored frame turns the primitive inside out
        out.invert()
    return out


def card(part: trimesh.Trimesh):
    """A tiny piece as one flat pyramid: base at the wide end, tip at the far end of its main axis."""
    V = np.asarray(part.vertices)
    c = V.mean(0)
    _, S, Vt = np.linalg.svd(V - c, full_matrices=False)
    ax, wide, thin = Vt[0], Vt[1], Vt[2]
    t = (V - c) @ ax
    w = (V - c) @ wide
    lo, hi = t.min(), t.max()
    band = np.abs(t - lo) < (hi - lo) * .3  # which end is wide: that one is the root
    if np.ptp(w[band]) < np.ptp(w[np.abs(t - hi) < (hi - lo) * .3]):
        ax, lo, hi = -ax, -hi, -lo
    base, tip = c + ax * lo, c + ax * hi
    W, Th = max(np.ptp(w), 1e-3), max(np.ptp((V - c) @ thin), 1e-3)
    v = np.array([base + wide * W / 2, base - wide * W / 2, base + thin * Th, tip])
    m = trimesh.Trimesh(v, [[0, 1, 3], [1, 2, 3], [2, 0, 3], [0, 2, 1]], process=False)
    m.fix_normals()
    return m


def sheet(part: trimesh.Trimesh, cells=8):
    """A flat or gently bent piece (hair lock, hat fold) as ONE layer: a grid on its mid-plane pulled onto it, cut to its
    outline. A closed primitive here collapses into a thick slab."""
    T, ext = trimesh.bounds.oriented_bounds(part)
    thin = int(np.argmin(ext))
    a, b = [i for i in range(3) if i != thin]
    cell = max(ext) / cells
    na, nb = max(1, int(round(ext[a] / cell))), max(1, int(round(ext[b] / cell)))
    A, B = np.meshgrid(np.linspace(-ext[a] / 2, ext[a] / 2, na + 1), np.linspace(-ext[b] / 2, ext[b] / 2, nb + 1), indexing="ij")
    L = np.zeros((A.size, 3))
    L[:, a], L[:, b] = A.ravel(), B.ravel()
    inv = np.linalg.inv(T)
    s = Sampler(part, count=max(20000, len(part.faces) * 400))
    P = s.project(trimesh.transform_points(L, inv))[0]
    lat = trimesh.transform_points(P, T) - L
    ok = np.hypot(lat[:, a], lat[:, b]) < .75 * max(ext[a] / na, ext[b] / nb)
    i = np.arange(A.size).reshape(A.shape)
    q = np.stack([i[:-1, :-1], i[1:, :-1], i[1:, 1:], i[:-1, 1:]], -1).reshape(-1, 4)
    q = q[ok[q].all(1)]
    if not len(q):
        return card(part)
    m = trimesh.Trimesh(P, np.vstack([q[:, [0, 1, 2]], q[:, [0, 2, 3]]]), process=False)
    m.remove_unreferenced_vertices()
    return m


def is_flat(part, ratio=.3):
    e = np.sort(trimesh.bounds.oriented_bounds(part)[1])
    return e[0] < ratio * e[1]


def rebuild(ref: trimesh.Trimesh, small=24, sub_for=lambda n: 1 if n < 150 else 2, root_near=None):  # noqa: E731
    """Every connected piece of the reference rebuilt: up to `small` triangles -> ribbon growing from root_near (hair) or
    card, flat -> one-layer sheet, bulky -> shrinkwrapped icosphere."""
    out = []
    for p in ref.split(only_watertight=False):
        if len(p.faces) <= small:
            out.append(ribbon(p, root_near) if root_near is not None else card(p))
        elif is_flat(p):
            out.append(sheet(p))
        else:
            out.append(shrinkwrap(p, sub_for(len(p.faces))))
    return trimesh.util.concatenate(out)


def unwrap(m: trimesh.Trimesh, sharp=60):
    """(V, F, UV) with our own atlas; UV in glTF convention (v down). Edges sharper than `sharp` degrees are split, so
    blocks keep crisp shading and the atlas is cut along them."""
    import xatlas
    m = trimesh.graph.smooth_shade(m, angle=np.radians(sharp)) if sharp else m
    vmap, F, uv = xatlas.parametrize(np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32))
    return np.asarray(m.vertices)[vmap], F.astype(np.int64), uv


def bake(V, F, UV, sampler: Sampler, size=512, pad=4):
    """Texture for our atlas: each covered texel takes the reference colour at the nearest surface point that faces the same way."""
    N = trimesh.Trimesh(V, F, process=False).vertex_normals
    img = np.zeros((size, size, 4), np.float32)
    px = UV * (size - 1)
    pts, nrm, where = [], [], []
    for f in F:
        a, b, c = px[f]
        lo, hi = np.floor(np.minimum(np.minimum(a, b), c)).astype(int), np.ceil(np.maximum(np.maximum(a, b), c)).astype(int)
        xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1))
        q = np.stack([xs.ravel(), ys.ravel()], 1).astype(float)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[1] - c[1]) * (q[:, 0] - c[0]) + (c[0] - b[0]) * (q[:, 1] - c[1])) / d
        l2 = ((c[1] - a[1]) * (q[:, 0] - c[0]) + (a[0] - c[0]) * (q[:, 1] - c[1])) / d
        l3 = 1 - l1 - l2
        e = -.02
        ins = (l1 >= e) & (l2 >= e) & (l3 >= e)
        if not ins.any():
            continue
        L = np.stack([l1, l2, l3], 1)[ins]
        pts.append(L @ V[f]), nrm.append(L @ N[f]), where.append(q[ins].astype(int))
    P, Nn, W = np.vstack(pts), np.vstack(nrm), np.vstack(where)
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-9
    _, f, bc = sampler.project(P, Nn)
    img[np.clip(W[:, 1], 0, size - 1), np.clip(W[:, 0], 0, size - 1)] = sampler.color_at(f, bc)
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGBA")
    for _ in range(pad):  # bleed colour into the gutters so mip-maps do not show seams
        grown = im.filter(ImageFilter.MaxFilter(3))
        im = Image.alpha_composite(grown, im)
    return im.convert("RGB")


# ---------------------------------------------------------------- clean parametric parts with a tidy UV layout
def ring(hx, hz, n=16, power=6.0):
    """Closed cross-section (superellipse, power 2 = ellipse, high = rounded rectangle). Starts at the back centre and
    runs through -X, front, +X, so the seam is at the back and the front reads left-to-right from outside."""
    t = np.pi + np.linspace(0, 2 * np.pi, n, endpoint=False)
    s, c = np.sin(t), np.cos(t)
    return np.c_[np.sign(s) * np.abs(s) ** (2 / power) * hx, np.sign(c) * np.abs(c) ** (2 / power) * hz]


def loft(frame, rings, n=16, power=6.0, caps=(True, True)):
    """Part along its own axis. frame: 4x4 local->world (local Y = part axis, +Z = front); rings: [(y, cx, cz, hx, hz)] from
    top to bottom. Returns (mesh, islands): islands = [(vertex ids, local uv (w units), (w, h))] for the atlas packer.
    Side = one strip (u around, v down the part), each cap = one island; vertices are split along island borders."""
    V, F, isl = [], [], []
    P = [np.c_[ring(hx, hz, n, power)[:, 0] + cx, np.full(n, y), ring(hx, hz, n, power)[:, 1] + cz] for y, cx, cz, hx, hz in rings]
    # side strip: n + 1 columns (seam duplicated)
    per = [np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([p, p[:1]]), axis=0), axis=1))] for p in P]
    W = max(x[-1] for x in per)
    vs = np.r_[0, np.cumsum([np.linalg.norm(np.mean(P[i + 1], 0) - np.mean(P[i], 0)) for i in range(len(P) - 1)])]
    ids = []
    for i, p in enumerate(P):
        pp = np.vstack([p, p[:1]])
        ids.append(np.arange(len(V), len(V) + n + 1))
        V += list(pp)
    uv = np.vstack([np.c_[per[i] / per[i][-1] * W, np.full(n + 1, vs[i])] for i in range(len(P))])
    for i in range(len(P) - 1):
        a, b = ids[i], ids[i + 1]
        for j in range(n):
            F += [[a[j], b[j], b[j + 1]], [a[j], b[j + 1], a[j + 1]]]
    isl.append((np.concatenate(ids), uv, (W, vs[-1])))
    for k, (on, p, top) in enumerate(((caps[0], P[0], True), (caps[1], P[-1], False))):
        if not on:
            continue
        c0 = len(V)
        V += list(p) + [p.mean(0)]
        for j in range(n):
            f = [c0 + j, c0 + (j + 1) % n, c0 + n]
            F.append(f if top else f[::-1])
        q = np.vstack([p, p.mean(0)])[:, [0, 2]]
        q = q - q.min(0)
        if not top:
            q[:, 1] = q[:, 1].max() - q[:, 1]  # bottom seen from below
        isl.append((np.arange(c0, c0 + n + 1), q, tuple(q.max(0))))
    m = trimesh.Trimesh(trimesh.transform_points(np.array(V), frame), np.array(F), process=False)
    if m.volume < 0:
        m.invert()
    return m, isl


def pack(islands, size=1024, pad=6):
    """Shelf-pack islands [(ids, uv in world units, (w, h))] into one square atlas with the same texel density.
    Returns uv per vertex (glTF convention) for ids 0..max."""
    order = sorted(range(len(islands)), key=lambda i: -islands[i][2][1])
    area = sum(w * h for _, _, (w, h) in islands)
    s = np.sqrt(area) * 1.25
    while True:  # find a shelf width that fits
        x = y = row = 0.0
        place = {}
        for i in order:
            w, h = islands[i][2]
            if x + w > s:
                x, y, row = 0.0, y + row, 0.0
            place[i] = (x, y)
            x += w + s * pad / size
            row = max(row, h + s * pad / size)
        if y + row <= s:
            break
        s *= 1.08
    n = max(int(ids.max()) for ids, _, _ in islands) + 1
    UV = np.zeros((n, 2))
    for i, (ids, uv, _) in enumerate(islands):
        UV[ids] = (uv + place[i]) / s
    return UV


def ribbon(part: trimesh.Trimesh, root_near):
    """A hair strand as a flat tapering ribbon along its own centre line: root (the end closer to root_near) wide, tip a point."""
    V = np.asarray(part.vertices)
    c = V.mean(0)
    _, _, Vt = np.linalg.svd(V - c, full_matrices=False)
    ax, wide = Vt[0], Vt[1]
    t = (V - c) @ ax
    if np.linalg.norm(c + ax * t.max() - root_near) < np.linalg.norm(c + ax * t.min() - root_near):
        ax, t = -ax, -t
    lo, hi = t.min(), t.max()
    pts = []
    for f, wf in ((0, 1), (.5, .6)):
        sel = np.abs(t - (lo + (hi - lo) * f)) <= (hi - lo) * .3
        cen = V[sel].mean(0) if sel.any() else c + ax * (lo + (hi - lo) * f)
        w = max(np.ptp((V[sel] - c) @ wide) if sel.sum() > 1 else 0, (hi - lo) * .08) * wf
        pts += [cen - wide * w / 2, cen + wide * w / 2]
    tip = V[np.argmax(t)]
    v = np.vstack([pts, [tip]])
    return trimesh.Trimesh(v, [[0, 1, 3], [0, 3, 2], [2, 3, 4]], process=False)
