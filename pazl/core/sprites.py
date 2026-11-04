"""2D sprites workshop: import/crop, colour-key background removal, pivot, sprite sheet pack/unpack.

Files: projects/sprites/<name>.png (+ <name>.json sidecar: pivot, frame rects for sheets)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def _side(p: Path) -> Path:
    return p.with_suffix(".json")


def info(p: Path) -> dict:
    im = Image.open(p)
    s = json.loads(_side(p).read_text("utf-8")) if _side(p).exists() else {}
    return {"size": list(im.size), **s}


def _wside(p: Path, **kw):
    s = json.loads(_side(p).read_text("utf-8")) if _side(p).exists() else {}
    s.update(kw)
    _side(p).write_text(json.dumps(s, ensure_ascii=False), "utf-8")


def colorkey(p: Path, color: str = "auto", tol: float = 0.12, soft: float = 0.06, out: Path | None = None) -> dict:
    """Makes pixels close to the key colour transparent (auto = most common border colour). Soft edge + despill."""
    a = np.asarray(Image.open(p).convert("RGBA"), np.float32) / 255
    rgb = a[..., :3]
    if color == "auto":
        b = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        q = (b * 31).round().astype(int)
        keys, cnt = np.unique(q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2], return_counts=True)
        k = keys[cnt.argmax()]
        key = np.array([k // 1024, (k // 32) % 32, k % 32], np.float32) / 31
    else:
        h = color.lstrip("#")
        key = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255
    d = np.linalg.norm(rgb - key, axis=-1) / np.sqrt(3)
    alpha = np.clip((d - tol) / max(soft, 1e-3), 0, 1)
    edge = (alpha > 0) & (alpha < 1)
    a2 = a.copy()
    # despill: remove key colour from semi-transparent edge pixels
    al = np.maximum(alpha[..., None], 1e-3)
    a2[..., :3] = np.where(edge[..., None], np.clip((rgb - key * (1 - al)) / al, 0, 1), rgb)
    a2[..., 3] = a[..., 3] * alpha
    out = out or p
    Image.fromarray((a2 * 255 + .5).astype(np.uint8), "RGBA").save(out)
    return {"key": "#%02x%02x%02x" % tuple((key * 255).round().astype(int)), "transparent": round(float((alpha == 0).mean()), 3)}


def trim(p: Path, pad: int = 1, box: list | None = None) -> dict:
    """Crops to box [x,y,w,h] or to the opaque bounding box."""
    im = Image.open(p).convert("RGBA")
    if box:
        x, y, w, h = map(int, box)
        bb = (x, y, x + w, y + h)
    else:
        bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox() or (0, 0, *im.size)
        bb = (max(bb[0] - pad, 0), max(bb[1] - pad, 0), min(bb[2] + pad, im.width), min(bb[3] + pad, im.height))
    im.crop(bb).save(p)
    return {"size": [bb[2] - bb[0], bb[3] - bb[1]]}


def set_pivot(p: Path, x: float, y: float) -> dict:
    """Pivot in 0..1 of the sprite (0.5, 1 = bottom centre)."""
    _wside(p, pivot=[round(float(x), 4), round(float(y), 4)])
    return info(p)


def pack_grid(ims: list, out: Path, cols: int = 0, pad: int = 0) -> dict:
    """Uniform grid sheet (cell = max frame size); writes out.png + out.json atlas."""
    cw = max(i.width for i in ims) + pad; ch = max(i.height for i in ims) + pad
    cols = cols or int(np.ceil(np.sqrt(len(ims))))
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cw, rows * ch), (0, 0, 0, 0))
    frames = []
    for i, im in enumerate(ims):
        x, y = (i % cols) * cw + (cw - im.width) // 2, (i // cols) * ch + (ch - im.height) // 2
        sheet.paste(im.convert("RGBA"), (x, y))
        frames.append([(i % cols) * cw, (i // cols) * ch, cw, ch])
    sheet.save(out)
    atlas = {"cell": [cw, ch], "cols": cols, "rows": rows, "count": len(ims), "frames": frames}
    _wside(Path(out), **atlas)
    return {"size": list(sheet.size), "cell": [cw, ch], "cols": cols, "rows": rows, "count": len(ims)}


def pack(paths: list[Path], out: Path, cols: int = 0, pad: int = 2) -> dict:
    return pack_grid([Image.open(p).convert("RGBA") for p in paths], out, cols, pad)


def unpack(p: Path, out_dir: Path, cols: int = 0, rows: int = 0, min_px: int = 16) -> dict:
    """Splits a sheet into frames: by grid (cols x rows) or, if not given, by opaque islands (auto)."""
    im = Image.open(p).convert("RGBA")
    out_dir.mkdir(parents=True, exist_ok=True)
    boxes = []
    if cols and rows:
        cw, ch = im.width // cols, im.height // rows
        boxes = [(c * cw, r * ch, (c + 1) * cw, (r + 1) * ch) for r in range(rows) for c in range(cols)]
    else:
        a = np.asarray(im)[..., 3] > 8
        lab, n = ndi.label(ndi.binary_dilation(a, iterations=2))
        for sl in ndi.find_objects(lab):
            if (sl[0].stop - sl[0].start) * (sl[1].stop - sl[1].start) >= min_px:
                boxes.append((sl[1].start, sl[0].start, sl[1].stop, sl[0].stop))
        boxes.sort(key=lambda b: (b[1] // 16, b[0]))
    files = []
    for i, b in enumerate(boxes):
        f = out_dir / f"{i + 1:03d}.png"
        im.crop(b).save(f); files.append(f.name)
    return {"count": len(files), "dir": out_dir.as_posix()}


def make_sample(root: Path) -> Path:
    """Procedural sprite on a magenta key background (for testing colour key / pack)."""
    from PIL import ImageDraw
    root.mkdir(parents=True, exist_ok=True)
    p = root / "sample_star.png"
    im = Image.new("RGBA", (96, 96), (255, 0, 255, 255))
    d = ImageDraw.Draw(im)
    pts = [(48 + (40 if i % 2 == 0 else 17) * np.cos(np.pi / 5 * i - np.pi / 2),
            50 + (40 if i % 2 == 0 else 17) * np.sin(np.pi / 5 * i - np.pi / 2)) for i in range(10)]
    d.polygon(pts, fill=(255, 205, 40), outline=(120, 70, 0), width=3)
    im.save(p)
    return p
