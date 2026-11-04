"""Mesh defects of a model by code: holes / tears, flipped or inside-out parts, slivers, body poking through clothes,
flickering coincident surfaces. Prints a short summary and the problems with plain places; --json for everything.

    .venv/Scripts/python.exe scripts/mesh_check.py chars/hero.glb [--openings] [--json]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from pazl.core import meshcheck  # noqa: E402

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    r = meshcheck.check(args[0], openings="--openings" in sys.argv)
    if "--json" in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f"{r['model']}: {r['tris']} tris, size {r['size']}, problems {r['summary'] or 'none'}")
        for p in r["problems"][:20]:
            extra = {k: v for k, v in p.items() if k not in ("kind", "part", "where", "at")}
            print(f"  {p['kind']:13} {p['part']:28} {p['where']:32} at {p['at']} {extra}")
