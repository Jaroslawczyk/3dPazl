"""2D frames workshop: keyframe sequences, inbetweening, quality check and export.

A sequence lives in projects/frames2d/<seq>/: key/0001.png... (keyframes), out/0001.png... (keys + generated
inbetweens, rebuilt by interpolate()), meta.json (fps, method, scores), export files (anim.gif, sheet.png, contact.png).

Inbetweening (native, numpy + scipy only): coarse-to-fine dense Lucas-Kanade optical flow in both directions,
backward warp of both keys to time t (Super-SloMo style approximation), blend weighted by t and forward-backward
consistency (occlusions). Line-art mode computes flow on a distance-to-line field (smooth everywhere, so thin lines
are tracked) and re-crisps lines after the blend. Ideas follow RIFE / DAIN / InterpAny-Clearer papers (MIT); no code
was copied. Optional external RIFE: set PAZL_RIFE to a rife-ncnn-vulkan executable (MIT, nihui)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

# ---------------------------------------------------------------- io


def load(p) -> np.ndarray:
    """RGBA float32 [0,1], HxWx4."""
    return np.asarray(Image.open(p).convert("RGBA"), np.float32) / 255.0


def save(a: np.ndarray, p) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(p)


def _gray(a):  # composite on white, luminance
    rgb = a[..., :3] * a[..., 3:] + (1 - a[..., 3:])
    return rgb @ np.float32([0.299, 0.587, 0.114])


def keys(seq: Path) -> list[Path]:
    return sorted((seq / "key").glob("*.png"))


def outs(seq: Path) -> list[Path]:
    return sorted((seq / "out").glob("*.png"))


def meta(seq: Path) -> dict:
    f = seq / "meta.json"
    return json.loads(f.read_text("utf-8")) if f.exists() else {"fps": 12}


def _wmeta(seq: Path, m: dict):
    (seq / "meta.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), "utf-8")


def is_lineart(a: np.ndarray) -> bool:
    g = _gray(a)
    return float((g < 0.5).mean()) < 0.12 and float(np.abs(a[..., 0] - a[..., 2]).mean()) < 0.03

# ---------------------------------------------------------------- optical flow


def _warp(img, u, v):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    c = [yy + v, xx + u]
    if img.ndim == 2:
        return ndi.map_coordinates(img, c, order=1, mode="nearest")
    return np.stack([ndi.map_coordinates(img[..., k], c, order=1, mode="nearest") for k in range(img.shape[2])], -1)


def _blockmatch(A, B, r: int | None = None, blk: float = 2.0):
    """Coarse level: exhaustive search of displacements (handles big cartoon moves LK cannot)."""
    r = r or max(2, max(A.shape) // 2)
    h, w = A.shape
    Bp = np.pad(B, r, mode="edge")
    best = np.full(A.shape, np.inf, np.float32); u = np.zeros_like(A); v = np.zeros_like(A)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            c = ndi.gaussian_filter(np.abs(A - Bp[r + dy:r + dy + h, r + dx:r + dx + w]), blk) + 1e-4 * (dx * dx + dy * dy)
            m = c < best
            best[m] = c[m]; u[m] = dx; v[m] = dy
    return ndi.median_filter(u, 3), ndi.median_filter(v, 3)


def flow(a: np.ndarray, b: np.ndarray, levels: int = 7, iters: int = 6, win: float = 3.0):
    """Dense flow u,v (pixels) with a(x) ≈ b(x + f(x)). a, b: 2D float images."""
    pa, pb = [a], [b]
    for _ in range(levels - 1):
        if min(pa[-1].shape) < 32:
            break
        pa.append(ndi.zoom(ndi.gaussian_filter(pa[-1], 1), 0.5, order=1))
        pb.append(ndi.zoom(ndi.gaussian_filter(pb[-1], 1), 0.5, order=1))
    u = v = None
    for A, B in zip(pa[::-1], pb[::-1]):
        if u is None:
            u, v = _blockmatch(A, B)
        else:
            zy, zx = A.shape[0] / u.shape[0], A.shape[1] / u.shape[1]
            u = ndi.zoom(u, (zy, zx), order=1)[:A.shape[0], :A.shape[1]] * 2
            v = ndi.zoom(v, (zy, zx), order=1)[:A.shape[0], :A.shape[1]] * 2
        for _ in range(iters):
            Bw = _warp(B, u, v)
            m = (A + Bw) / 2
            Iy, Ix = np.gradient(m)
            It = Bw - A
            g = lambda x: ndi.gaussian_filter(x, win)
            sxx, syy, sxy, sxt, syt = g(Ix * Ix), g(Iy * Iy), g(Ix * Iy), g(Ix * It), g(Iy * It)
            reg = 1e-3 + 0.05 * float(sxx.mean() + syy.mean())
            det = (sxx + reg) * (syy + reg) - sxy * sxy
            u = u - np.clip(((syy + reg) * sxt - sxy * syt) / det, -1, 1)
            v = v - np.clip(((sxx + reg) * syt - sxy * sxt) / det, -1, 1)
            u = ndi.median_filter(u, 5); v = ndi.median_filter(v, 5)
    return u.astype(np.float32), v.astype(np.float32)


def _flow_src(a, lineart):
    # distance-to-edge field: smooth and textured everywhere, so LK tracks thin strokes and flat cel fills
    g = ndi.gaussian_filter(_gray(a), 0.8)
    edge = (g < 0.6) if lineart else (np.hypot(*np.gradient(g)) > 0.04)
    d = ndi.distance_transform_edt(~edge)
    c = max(a.shape[:2]) / 4
    return (np.sqrt(np.clip(d / c, 0, 1)) * 0.8 + 0.2 * g).astype(np.float32)


def _project(u, v, t, conf):
    """Flow projection to time t (idea of DAIN's projection layer): splat each source pixel to p + t*f, keep the
    most confident / fastest-moving one (cel foreground), fill holes from the nearest written pixel.
    Returns backward flow (ut, vt) at time t pointing into the source frame."""
    h, w = u.shape
    yy, xx = np.mgrid[0:h, 0:w]
    qx = np.clip(np.rint(xx + t * u), 0, w - 1).astype(int); qy = np.clip(np.rint(yy + t * v), 0, h - 1).astype(int)
    pr = (conf * (1 + np.hypot(u, v))).ravel()
    o = np.argsort(pr, kind="stable")  # low priority first, later writes win
    idx = (qy.ravel() * w + qx.ravel())[o]
    ut = np.zeros(h * w, np.float32); vt = np.zeros(h * w, np.float32); hit = np.zeros(h * w, bool)
    ut[idx] = -t * u.ravel()[o]; vt[idx] = -t * v.ravel()[o]; hit[idx] = True
    ut, vt, hit = ut.reshape(h, w), vt.reshape(h, w), hit.reshape(h, w)
    if not hit.all():
        iy, ix = ndi.distance_transform_edt(~hit, return_distances=False, return_indices=True)
        ut, vt = ut[iy, ix], vt[iy, ix]
    return ndi.median_filter(ut, 3), ndi.median_filter(vt, 3)


def inbetween(a: np.ndarray, b: np.ndarray, ts: list[float], lineart: bool | None = None, fl=None):
    """Returns ([frames], ghost scores). ghost = mean |warp0 - warp1| on content pixels (0 = both keys agree)."""
    if lineart is None:
        lineart = is_lineart(a) and is_lineart(b)
    if fl is None:
        sa, sb = _flow_src(a, lineart), _flow_src(b, lineart)
        fl = flow(sa, sb), flow(sb, sa)
    (u01, v01), (u10, v10) = fl
    # forward-backward consistency -> occlusion confidence
    e0 = np.hypot(u01 + _warp(u10, u01, v01), v01 + _warp(v10, u01, v01))
    e1 = np.hypot(u10 + _warp(u01, u10, v10), v10 + _warp(v01, u10, v10))
    c0, c1 = np.exp(-(e0 / 3) ** 2), np.exp(-(e1 / 3) ** 2)
    res, ghosts = [], []
    for t in ts:
        ut0, vt0 = _project(u01, v01, t, c0)
        ut1, vt1 = _project(u10, v10, 1 - t, c1)
        w0, w1 = _warp(a, ut0, vt0), _warp(b, ut1, vt1)
        k0 = (1 - t) * _warp(c0, ut0, vt0) + 1e-3
        k1 = t * _warp(c1, ut1, vt1) + 1e-3
        o = (w0 * k0[..., None] + w1 * k1[..., None]) / (k0 + k1)[..., None]
        g0, g1 = _gray(w0), _gray(w1)
        content = (g0 < 0.8) | (g1 < 0.8)
        ghosts.append(round(float(np.abs(g0 - g1)[content].mean()) if content.any() else 0.0, 3))
        if lineart:
            d = 1 - _gray(o)
            k = np.clip((d - 0.2) / 0.3, 0, 1); k = k * k * (3 - 2 * k)
            stroke = np.minimum(w0[..., :3], w1[..., :3]) if t == 0.5 else (w0 if t < 0.5 else w1)[..., :3]
            o = o.copy()
            o[..., :3] = (1 - k[..., None]) * 1.0 + k[..., None] * np.minimum(stroke, o[..., :3])
            o[..., 3] = np.maximum(o[..., 3], k)
        res.append(o)
    return res, ghosts


def _rife(pa: Path, pb: Path, ts: list[float]):
    exe = os.environ.get("PAZL_RIFE") or shutil.which("rife-ncnn-vulkan")
    if not exe:
        raise RuntimeError("RIFE не найден: задайте PAZL_RIFE = путь к rife-ncnn-vulkan(.exe)")
    out = []
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(ts):
            o = Path(td) / f"{i}.png"
            subprocess.run([exe, "-0", str(pa), "-1", str(pb), "-o", str(o), "-s", str(t)], check=True,
                           capture_output=True, timeout=300)
            out.append(load(o))
    return out

# ---------------------------------------------------------------- sequence ops


def interpolate(seq: Path, n: int = 1, method: str = "flow", lineart: bool | None = None, fps: int | None = None) -> dict:
    """Builds out/ = keys with n inbetweens between each pair. method: flow | blend | rife."""
    ks = keys(seq)
    if len(ks) < 2:
        raise ValueError("нужно минимум 2 ключевых кадра в key/")
    od = seq / "out"
    shutil.rmtree(od, ignore_errors=True); od.mkdir(parents=True)
    ts = [(i + 1) / (n + 1) for i in range(n)]
    idx, pairs = 1, []
    imgs = [load(k) for k in ks]
    for i in range(len(ks) - 1):
        save(imgs[i], od / f"{idx:04d}.png"); idx += 1
        a, b = imgs[i], imgs[i + 1]
        if b.shape != a.shape:
            b = np.asarray(Image.fromarray((b * 255).astype(np.uint8)).resize(a.shape[1::-1]), np.float32) / 255
        if method == "blend":
            fr = [a * (1 - t) + b * t for t in ts]
            gh = [round(float(np.abs(_gray(a) - _gray(b)).mean()), 3)] * n
        elif method == "rife":
            fr = _rife(ks[i], ks[i + 1], ts)
            gh = [None] * n
        else:
            fr, gh = inbetween(a, b, ts, lineart)
        for f in fr:
            save(f, od / f"{idx:04d}.png"); idx += 1
        pairs.append({"pair": f"{ks[i].stem}->{ks[i + 1].stem}", "ghost": gh})
    save(imgs[-1], od / f"{idx:04d}.png")
    m = meta(seq)
    m.update({"n": n, "method": method, "pairs": pairs, "frames": idx})
    if fps:
        m["fps"] = int(fps)
    _wmeta(seq, m)
    return {"frames": idx, "keys": len(ks), "pairs": pairs}


def check(seq: Path) -> dict:
    """Compact quality report: size, frame count, ghosting per pair, pacing flicker, contact sheet path."""
    fs = outs(seq) or keys(seq)
    if not fs:
        raise ValueError("пустая последовательность")
    gs = [_gray(load(f)) for f in fs]
    d = np.array([np.abs(gs[i + 1] - gs[i]).mean() for i in range(len(gs) - 1)]) if len(gs) > 1 else np.zeros(1)
    flick = round(float(d.std() / (d.mean() + 1e-6)), 3)  # 0 = even motion pacing
    jumps = [i + 1 for i in range(len(d)) if d[i] > 2.2 * np.median(d) and np.median(d) > 0]
    m = meta(seq)
    contact_sheet(seq)
    h, w = gs[0].shape
    return {"frames": len(fs), "size": [w, h], "fps": m.get("fps", 12), "method": m.get("method"),
            "pacing_flicker": flick, "jumps_at": jumps[:10], "pairs": m.get("pairs", []),
            "contact": (seq / "contact.png").as_posix()}


def contact_sheet(seq: Path, cell: int = 128, cols: int = 8) -> Path:
    """Small grid of all output frames with numbers: keys framed blue, inbetweens orange (one image for AI review)."""
    from PIL import ImageDraw
    fs = outs(seq) or keys(seq)
    knames = {k.stem for k in keys(seq)}
    m = meta(seq); n = m.get("n", 0) if outs(seq) else 0
    fs = fs[:64]
    rows = (len(fs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (40, 40, 44))
    dr = ImageDraw.Draw(sheet)
    for i, f in enumerate(fs):
        im = Image.open(f).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        im = bg.convert("RGB"); im.thumbnail((cell - 6, cell - 6))
        x, y = (i % cols) * cell, (i // cols) * cell
        key = (i % (n + 1) == 0) if n else (f.stem in knames)
        dr.rectangle([x + 1, y + 1, x + cell - 2, y + cell - 2], outline=(70, 140, 255) if key else (255, 150, 40), width=2)
        sheet.paste(im, (x + 3, y + 3))
        dr.text((x + 6, y + cell - 16), str(i + 1), fill=(220, 30, 30))
    p = seq / "contact.png"
    sheet.save(p)
    return p


def _frames_rgba(seq: Path, size: int | None = None):
    fs = outs(seq) or keys(seq)
    ims = [Image.open(f).convert("RGBA") for f in fs]
    if size:
        for im in ims:
            im.thumbnail((size, size))
    return ims


def export_gif(seq: Path, fps: int | None = None, size: int | None = 512) -> Path:
    fps = fps or meta(seq).get("fps", 12)
    ims = []
    for im in _frames_rgba(seq, size):
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        ims.append(bg.convert("P", palette=Image.ADAPTIVE))
    p = seq / "anim.gif"
    ims[0].save(p, save_all=True, append_images=ims[1:], duration=int(1000 / fps), loop=0, disposal=2)
    return p


def export_sheet(seq: Path, cols: int = 0, size: int | None = None) -> dict:
    from . import sprites
    ims = _frames_rgba(seq, size)
    p = seq / "sheet.png"
    atlas = sprites.pack_grid(ims, p, cols)
    return {"path": p.as_posix(), **atlas}


def make_sample(root: Path, name: str = "sample") -> Path:
    """Procedural test keyframes (no external data): a bouncing ball with squash, as sketch and as colour."""
    from PIL import ImageDraw
    poses = [(64, 50, 1.0), (128, 170, 1.25), (192, 60, 1.0), (240, 175, 1.3)]
    for kind in ("sketch", "color"):
        seq = root / f"{name}_{kind}"
        (seq / "key").mkdir(parents=True, exist_ok=True)
        for i, (x, y, sq) in enumerate(poses):
            im = Image.new("RGBA", (320, 240), (255, 255, 255, 255))
            d = ImageDraw.Draw(im)
            rx, ry = 26 * sq, 26 / sq
            d.line([0, 205, 320, 205], fill=(0, 0, 0), width=2)
            if kind == "color":
                d.ellipse([x - rx + 6, 200, x + rx + 6, 210], fill=(180, 180, 190))
                d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=(230, 80, 60), outline=(30, 20, 20), width=3)
                d.arc([x - rx * .6, y - ry * .7, x + rx * .2, y], 200, 280, fill=(255, 220, 210), width=4)
            else:
                d.ellipse([x - rx, y - ry, x + rx, y + ry], outline=(0, 0, 0), width=3)
                d.arc([x - rx * .7, y - ry * .7, x + rx * .7, y + ry * .7], 200, 300, fill=(0, 0, 0), width=2)
            im.save(seq / "key" / f"{i + 1:04d}.png")
        _wmeta(seq, {"fps": 12})
    return root / f"{name}_sketch"
