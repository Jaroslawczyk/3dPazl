"""Roblox avatar outfit from the user's references: olive canvas jacket, dark tee, dark loose pants, black sneakers.
Textures are CC0 Poly Haven fabrics (rough_linen, cotton_jersey, jogging_melange) tinted to the target colour.
Run: .venv/Scripts/python.exe scripts/create_roblox_outfit.py  -> projects/chars/roblox_outfit.glb"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from pazl.core import chars, skins

S = Path("projects/skins")
TINTS = (("rough_linen", "olive_canvas", (118, 118, 62)), ("cotton_jersey", "dark_jersey", (34, 48, 44)),
         ("jogging_melange", "dark_pants", (36, 40, 41)))


def tint(src, dst, rgb):
    if not (S / f"web_{src}.jpg").exists():
        skins.web_download("polyhaven", src)
    im = np.asarray(Image.open(S / f"web_{src}.jpg").convert("RGB")).astype(float)
    g = im.mean(axis=2, keepdims=True)
    Image.fromarray(np.clip(g / g.mean() * np.array(rgb, float), 0, 255).astype("uint8")).save(S / f"web_{dst}.jpg", quality=92)
    j = json.loads((S / f"web_{src}.skin.json").read_text("utf-8"))
    j.update(file=f"skins/web_{dst}.jpg", title=dst)
    (S / f"web_{dst}.skin.json").write_text(json.dumps(j), "utf-8")


for t in TINTS:
    tint(*t)
chars.create("roblox_outfit", preset="roblox", quality="mid")
c = chars.load("roblox_outfit")
c["cloth3d"], c["quality"] = True, "low"
chars.save(c)
for kind, skin, col, bt in (("pants", "web_dark_pants", "#23282a", 700), ("tank", "web_dark_jersey", "#26332f", 500),
                            ("jacket", "web_olive_canvas", "#7c7c45", 1300), ("shoes", None, "#1c1c1f", 400)):
    chars.wear("roblox_outfit", kind, color=col, skin=skin, block_tris=bt, **({"ease": .028} if kind == "jacket" else {}))
print(chars.export("roblox_outfit")["tris"])
