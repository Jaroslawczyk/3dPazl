"""Dev check: build every macro (in its style), validate, render a contact sheet each.

    python scripts/check_all.py [macro ...]
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pazl.core import elements  # noqa: F401,E402
from pazl.core.builder import build  # noqa: E402
from pazl.core.mesh import validate  # noqa: E402
from pazl.core.registry import ELEMENTS  # noqa: E402
from pazl.core.render import render_sheet  # noqa: E402
from pazl.core.styles import load_styles  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "projects" / "_check"


def style_for(macro):
    for s in load_styles().values():
        if macro in s.get("macros", []) and s["id"] != "generic":
            return s["id"]
    return "generic"


def main(names):
    names = names or [n for n, e in ELEMENTS.items() if e.macro]
    for n in names:
        recipe = {"name": n, "style": style_for(n), "elements": [{"id": "b", "type": n}]}
        t = time.time()
        res = build(recipe)
        rep = validate(res)
        bad = sorted({e for f in rep.get("floating", []) for e in f["elements"]})
        render_sheet(res.final(), OUT / f"{n}.png", highlight=bad, title=f"{n} [{recipe['style']}]")
        print(f"{n:20s} ok={rep['ok']} tris={rep.get('triangles')} t={time.time() - t:.1f}s "
              f"errors={json.dumps(rep['errors'], ensure_ascii=False, default=str)[:600]}")


if __name__ == "__main__":
    main(sys.argv[1:])
