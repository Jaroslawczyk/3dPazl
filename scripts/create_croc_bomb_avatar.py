"""Roblox avatar: tank top with a crocodile print + a bomb-with-fuse hat. Texture slot: projects/skins/prints/croc_tank.png (Grok)."""
from pazl.core import chars, roblox, meshcheck  # noqa: F401

NAME = "croc_bomb"
chars.create(NAME, preset="roblox", quality="mid")
chars.wear(NAME, "tank", color="#f2f2f2", print="skins/prints/croc_tank.png", print_size=.7)
chars.wear(NAME, "pants", color="#2f3a55")
chars.wear(NAME, "shoes", color="#2a2a2e")
chars.wear(NAME, "bomb_hat", as_head=True, body_skin={"title": "Bomb metal", "pattern": "image", "file": "skins/bomb_albedo.png", "tile": .6, "rough": .5, "normal_map": "skins/bomb_normal.png", "rough_map": "skins/bomb_rough.png", "ao_map": "skins/bomb_ao.png"})
import json, pathlib  # the bomb head swallows the head block on purpose: auto-fix would fight it
f = pathlib.Path("projects/chars") / f"{NAME}.char.json"
d = json.loads(f.read_text(encoding="utf-8")); d["no_fix"] = True; f.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
print(chars.export(NAME)["tris"])
roblox.export_char(NAME)
