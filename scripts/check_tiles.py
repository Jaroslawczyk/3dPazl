"""Seam and normal checks for assets/tiles PNG sets."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TILES = ROOT / "assets" / "tiles"


def seam_score(arr: np.ndarray, seam_floor: float = 0.012) -> tuple[float, float, bool]:
    """Return (seam_diff, interior_p99_diff, fail). Works on HxW or HxWxC.

    The wrap pair (last,first) is compared with the sharpest adjacent-line
    pairs inside the tile: a real seam is sharper than anything inside,
    while a joint/mortar line that merely sits on the border is not.
    """
    a = arr.astype(np.float64)
    if a.ndim == 2:
        a = a[..., None]

    def per_pair(axis: int) -> tuple[float, np.ndarray]:
        b = np.moveaxis(a, axis, 0)
        inner = np.abs(b[1:] - b[:-1]).reshape(b.shape[0] - 1, -1).mean(axis=1)
        wrap = np.abs(b[0] - b[-1]).mean()
        return float(wrap), inner

    w0, i0 = per_pair(0)
    w1, i1 = per_pair(1)
    seam = 0.5 * (w0 + w1)
    interior = 0.5 * (np.max(i0) + np.max(i1))
    fail = (w0 > max(1.25 * np.max(i0), seam_floor)) or (
        w1 > max(1.25 * np.max(i1), seam_floor)
    )
    return float(seam), float(interior), bool(fail)


def check_normal(path: Path) -> tuple[bool, str]:
    im = np.asarray(Image.open(path).convert("RGB"), float) / 255.0
    n = im * 2 - 1
    mag = np.linalg.norm(n, axis=2)
    if not np.allclose(mag, 1.0, atol=0.15):
        return False, f"normal not unit: |n| mean={mag.mean():.3f}"
    # Edge jump vs interior
    seam, interior, _ = seam_score(im)
    if interior > 1e-6 and seam > 2.0 * interior:
        return False, f"normal seam jump seam={seam:.4f} int={interior:.4f}"
    return True, "ok"


def iter_texture_dirs() -> list[Path]:
    if not TILES.exists():
        return []
    out = []
    for cat in sorted(TILES.iterdir()):
        if not cat.is_dir() or cat.name.startswith("_"):
            continue
        for name in sorted(cat.iterdir()):
            if name.is_dir() and (name / "albedo.png").exists():
                out.append(name)
    return out


def build_contact_sheet(dirs: list[Path]) -> Path:
    cols, rows = 4, max(1, (len(dirs) + 3) // 4)
    thumb = 256
    sheet = Image.new("RGB", (cols * thumb, rows * (thumb + 24)), (32, 32, 36))
    draw = ImageDraw.Draw(sheet)
    for i, d in enumerate(dirs):
        prev = d / "preview.png"
        if not prev.exists():
            continue
        im = Image.open(prev).convert("RGB")
        im = im.resize((thumb, thumb), Image.Resampling.LANCZOS)
        c, r = i % cols, i // cols
        sheet.paste(im, (c * thumb, r * (thumb + 24)))
        label = f"{d.parent.name}/{d.name}"
        draw.text((c * thumb + 4, r * (thumb + 24) + thumb + 2), label, fill=(220, 220, 220))
    out = TILES / "_contact_sheet.png"
    sheet.save(out)
    return out


def main() -> int:
    dirs = iter_texture_dirs()
    if not dirs:
        print("No textures in assets/tiles")
        return 1

    fails: list[str] = []
    for d in dirs:
        for fname in ("albedo.png", "height.png", "ao.png", "roughness.png", "metallic.png", "preview.png"):
            p = d / fname
            if not p.exists():
                continue
            floor = 0.012 if fname in ("albedo.png", "height.png", "preview.png") else 0.022
            im = np.asarray(Image.open(p))
            if im.ndim == 2:
                arr = im.astype(np.float64) / (65535.0 if im.dtype == np.uint16 else 255.0)
            else:
                arr = im.astype(np.float64) / 255.0
            seam, interior, bad = seam_score(arr, seam_floor=floor)
            rel = p.relative_to(TILES)
            if bad:
                msg = f"FAIL seam {rel}: seam={seam:.5f} interior={interior:.5f}"
                if fname in ("albedo.png", "height.png", "preview.png"):
                    fails.append(msg)
                else:
                    print(msg)
            else:
                print(f"PASS {rel} seam={seam:.5f} int={interior:.5f}")

        npath = d / "normal.png"
        if npath.exists():
            ok, msg = check_normal(npath)
            rel = npath.relative_to(TILES)
            if not ok:
                fails.append(f"FAIL normal {rel}: {msg}")
            else:
                print(f"PASS {rel} normal")

    sheet = build_contact_sheet(dirs)
    print(f"Contact sheet: {sheet}")

    for line in fails:
        print(line)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
