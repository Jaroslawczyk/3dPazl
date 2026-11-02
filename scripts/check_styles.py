"""Dev check: every style (incl. sub-styles) builds its main macro, validates, exports (glb + obj, re-opened) and
renders a thumbnail; one contact sheet + a report.

    python scripts/check_styles.py [style ...]
"""
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import trimesh  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from pazl.core import elements  # noqa: F401,E402
from pazl.core.builder import build  # noqa: E402
from pazl.core.mesh import export, validate  # noqa: E402
from pazl.core.render import render_sheet  # noqa: E402
from pazl.core.styles import load_styles  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "projects" / "_check_styles"


def main(names):
    styles = load_styles()
    names = names or sorted(styles)
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    rows, tiles = [], []
    for sid in names:
        s = styles[sid]
        macro = (s.get("macros") or ["house"])[0]
        t = time.time()
        row = {"style": sid, "macro": macro}
        try:
            res = build({"name": sid, "style": sid, "detail": s.get("detail", "realistic"), "elements": [{"id": "b", "type": macro}]})
            rep = validate(res)
            row.update(ok=rep["ok"], tris=rep.get("triangles"), errors=[e["error"] for e in rep["errors"]][:3],
                       build_errors=[e["error"][:80] for e in res.errors][:3], zfight=rep.get("surfaces", {}).get("zfight"))
            for fmt in ("glb", "obj"):
                p, _ = export(res.final(), tmp / f"{sid}.{fmt}", fmt, None, textured=False, result=res)
                m = trimesh.load(str(p), force="mesh")
                row[f"{fmt}_faces"] = len(m.faces)
            png = OUT / f"{sid}.png"
            render_sheet(res.final(), png, views=["iso_fl"], tile=(300, 225), title=f"{sid} / {macro}")
            tiles.append((sid, png))
        except Exception as ex:  # report and keep going
            row.update(ok=False, crash=f"{type(ex).__name__}: {ex}"[:200])
        row["t"] = round(time.time() - t, 1)
        rows.append(row)
        flag = "OK " if row.get("ok") else "BAD"
        print(f"{flag} {sid:28s} {macro:18s} tris={row.get('tris')} t={row['t']}s "
              f"{row.get('crash') or row.get('build_errors') or row.get('errors') or ''}", flush=True)
    (OUT / "report.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), "utf-8")
    if tiles:  # contact sheet, 8 per row
        ims = [Image.open(p) for _, p in tiles]
        w, h = ims[0].size
        cols = 8
        sheet = Image.new("RGB", (w * cols, h * ((len(ims) + cols - 1) // cols)), (20, 20, 25))
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sheet.save(OUT / "_all_styles.png")
    bad = [r["style"] for r in rows if not r.get("ok")]
    print(f"\n{len(rows) - len(bad)}/{len(rows)} ok; problems: {bad}")


if __name__ == "__main__":
    main(sys.argv[1:])
