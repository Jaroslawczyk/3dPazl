"""Offscreen rendering: contact sheet of many views in ONE image (cheap for an AI to look at)."""
from __future__ import annotations

import math
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

from . import geo as g
from .materials import MATS
from .mesh import manifold_to_arrays, tri_materials

def _font(size=13):
    for f in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


_EXEC = ThreadPoolExecutor(max_workers=1)  # all GL work in one thread
_R = {}

VIEWS = {  # name: (azimuth deg from +X counter-clockwise, elevation deg)
    "front": (-90, 8), "right": (0, 8), "back": (90, 8), "left": (180, 8),
    "iso_fl": (-135, 32), "iso_fr": (-45, 32), "iso_br": (45, 32), "iso_bl": (135, 32),
    "top": (-90, 89), "below": (-60, -35), "section_x": (20, 30), "section_y": (-70, 30),
    "eye_fl": (-120, 2), "eye_fr": (-60, 2), "eye_br": (60, 2), "eye_bl": (120, 2),
    # cuts are looked at from an angle and close up: floors, walls and textures inside must be checked too
    "plan": (-60, 62), "plan_mid": (-60, 62),
}
DEFAULT_VIEWS = ["front", "right", "back", "left", "iso_fl", "iso_fr", "iso_br", "iso_bl",
                 "eye_fl", "eye_fr", "eye_br", "top", "below", "section_x", "plan", "plan_mid"]
VIEW_RU = {"front": "спереди", "right": "справа", "back": "сзади", "left": "слева", "iso_fl": "3/4 перед-лево",
           "iso_fr": "3/4 перед-право", "iso_br": "3/4 зад-право", "iso_bl": "3/4 зад-лево", "top": "сверху",
           "below": "снизу", "section_x": "разрез X", "section_y": "разрез Y", "eye_fl": "с земли перед-лево",
           "eye_fr": "с земли перед-право", "eye_br": "с земли зад-право", "eye_bl": "с земли зад-лево",
           "plan": "план 1 этажа (разрез)", "plan_mid": "план середины (разрез)"}


def look_at(eye, target, up=(0, 0, 1)):
    eye, target, up = map(lambda v: np.asarray(v, float), (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    if abs(np.dot(f, up)) > 0.999:
        up = np.array([0, 1.0, 0])
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = s, u, -f, eye
    return m


def camera_for(view, center, radius, fov=40.0, az=None, el=None, dist=None):
    a, e = VIEWS.get(view, (-45, 30)) if az is None else (az, el)
    d = dist or radius / math.sin(math.radians(fov) / 2) * 1.08
    a, e = math.radians(a), math.radians(e)
    eye = center + d * np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    return look_at(eye, center), eye


def _tm_from_manifold(m, highlight=()):
    V, F, oid = manifold_to_arrays(m)
    mats, elems = tri_materials(oid)
    cols = np.array([list(MATS.get(n).get("color", [200, 200, 200])) + [255] for n in mats], dtype=np.uint8)
    if highlight:
        hl = np.isin(elems, list(highlight))
        cols[hl] = [255, 30, 30, 255]
    tm = trimesh.Trimesh(V, F, process=False)
    tm.visual = trimesh.visual.ColorVisuals(tm, face_colors=cols)
    return tm


def _render_job(final, views, tile, highlight, out_path, title, custom, extra=()):
    import pyrender
    mn, mx = g.bbox(final)
    center = (mn + mx) / 2
    radius = float(np.linalg.norm(mx - mn) / 2) or 1.0
    base_tm = _tm_from_manifold(final, highlight)
    size = (tile[0], tile[1])
    key = size
    if key not in _R:
        _R[key] = pyrender.OffscreenRenderer(*size)
    r = _R[key]
    ground_r = radius * 3
    ground = trimesh.creation.cylinder(radius=ground_r, height=0.02, sections=48)
    ground.apply_translation([center[0], center[1], -0.011])
    ground.visual = trimesh.visual.ColorVisuals(ground, face_colors=[120, 130, 120, 255])
    images = []
    for v in views:
        tm, vc, vr = base_tm, center, radius
        cut = None
        if v in ("plan", "plan_mid"):  # horizontal cut (1st floor / mid height), looked at from above at an angle
            zc = float(mn[2] + (min(2.4, (mx[2] - mn[2]) * 0.35) if v == "plan" else (mx[2] - mn[2]) * 0.5))
            cut = final.trim_by_plane([0, 0, -1], -zc)
        elif v.startswith("section"):
            axis = [1, 0, 0] if v == "section_x" else [0, -1, 0]
            n = [-axis[0], -axis[1], 0]
            cut = final.trim_by_plane(n, float(np.dot(center, n)))
        if cut is not None and not cut.is_empty():
            tm = _tm_from_manifold(cut, highlight)
            cmn, cmx = g.bbox(cut)
            vc, vr = (cmn + cmx) / 2, float(np.linalg.norm(cmx - cmn) / 2) or radius
            if v.startswith("plan"):
                vr *= 0.8  # closer: rooms fill the tile
        sc = pyrender.Scene(ambient_light=[0.35, 0.35, 0.38], bg_color=[0.82, 0.88, 0.95, 1.0])
        sc.add(pyrender.Mesh.from_trimesh(tm, smooth=False))
        if cut is None:  # painted windows / doors (textured overlay quads) on the outside views
            for e in extra:
                sc.add(pyrender.Mesh.from_trimesh(e, smooth=False))
        if v not in ("below",):
            sc.add(pyrender.Mesh.from_trimesh(ground, smooth=False))
        if custom and v == "custom":
            pose, eye = camera_for(None, np.asarray(custom.get("target", center)), radius, custom.get("fov", 40),
                                   custom.get("az", -45), custom.get("el", 25), custom.get("dist"))
        elif v.startswith("eye_"):  # standing on the ground ~1.7 m high, a bit further away
            a = math.radians(VIEWS[v][0])
            dd = radius / math.sin(math.radians(20)) * 1.15
            eye = center + np.array([dd * math.cos(a), dd * math.sin(a), 0.0])
            eye[2] = mn[2] + 1.7
            pose = look_at(eye, [center[0], center[1], mn[2] + (mx[2] - mn[2]) * 0.4])
        else:
            pose, eye = camera_for(v, vc, vr)
        sc.add(pyrender.PerspectiveCamera(yfov=math.radians(40), aspectRatio=size[0] / size[1], znear=0.05, zfar=radius * 20), pose=pose)
        for la, le, inten in ((-50, 50, 3.2), (130, 35, 1.4), (40, -20, 0.6)):
            lp, _ = camera_for(None, center, radius, az=la, el=le)
            sc.add(pyrender.DirectionalLight(color=[1, 1, 1], intensity=inten), pose=lp)
        color, _ = r.render(sc)
        im = Image.fromarray(color)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, size[0], 18], fill=(30, 30, 40))
        d.text((5, 3), f"{v} ({VIEW_RU.get(v, v)})", fill=(255, 255, 255), font=_font(12))
        images.append(im)
    cols = 4 if len(images) > 4 else len(images)
    rows = math.ceil(len(images) / cols)
    sheet = Image.new("RGB", (cols * size[0], rows * size[1] + 22), (20, 20, 25))
    for i, im in enumerate(images):
        sheet.paste(im, ((i % cols) * size[0], 22 + (i // cols) * size[1]))
    d = ImageDraw.Draw(sheet)
    s = mx - mn
    d.text((6, 4), f"{title}   size {s[0]:.1f} x {s[1]:.1f} x {s[2]:.1f} m   tris {final.num_tri()}"
                   + (f"   RED = problems: {', '.join(list(highlight)[:6])}" if highlight else ""), fill=(255, 220, 120), font=_font(13))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    cams = [{"view": v, "pose": camera_for(v, center, radius)[0].tolist()} for v in views if v != "custom"]
    return {"path": str(out_path), "views": views, "cameras": cams, "center": center.tolist(), "radius": radius}


def render_sheet(final, out_path, views=None, tile=(384, 288), highlight=(), title="", custom=None, extra=()):
    """extra = textured trimeshes (Z-up) drawn on top of the shell in uncut views, e.g. painted windows."""
    views = views or DEFAULT_VIEWS
    return _EXEC.submit(_render_job, final, views, tile, tuple(highlight), out_path, title, custom, tuple(extra)).result()


def painted_meshes(result, n=12) -> list:
    """Painted windows/doors of painted styles for render_sheet(extra=...): each picture quad becomes an n x n grid of
    flat-coloured cells (the offscreen GL here cannot upload textures), Z-up."""
    from .decals import ensure_all, file_for
    from .mesh import overlay_meshes
    out = []
    for name, tm in overlay_meshes(result, {"painted"}, y_up=False):
        ensure_all()
        img = np.asarray(Image.open(file_for(name)).convert("RGB").resize((n, n)))[::-1]  # row 0 = bottom
        V, F, C = [], [], []
        for q in range(len(tm.vertices) // 4):
            p0, p1, _, p3 = tm.vertices[q * 4:q * 4 + 4]
            du, dv = (p1 - p0) / n, (p3 - p0) / n
            for j in range(n):
                for i in range(n):
                    k = len(V)
                    a = p0 + du * i + dv * j
                    V += [a, a + du, a + du + dv, a + dv]
                    F += [[k, k + 1, k + 2], [k, k + 2, k + 3]]
                    C += [img[j, i]] * 2
        m = trimesh.Trimesh(np.asarray(V), np.asarray(F), process=False)
        m.visual.face_colors = np.c_[np.asarray(C, np.uint8), np.full(len(C), 255, np.uint8)]
        out.append(m)
    return out
