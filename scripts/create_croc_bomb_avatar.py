"""Roblox avatar: tank top with a crocodile print + a bomb-with-fuse hat. Texture slot: projects/skins/prints/croc_tank.png (Grok)."""
from pazl.core import chars, roblox, meshcheck  # noqa: F401

NAME = "croc_bomb"
chars.create(NAME, preset="roblox", quality="mid")
chars.wear(NAME, "tank", color="#f2f2f2", print="skins/prints/croc_tank.png", print_size=.7)
chars.wear(NAME, "pants", color="#2f3a55")
chars.wear(NAME, "shoes", color="#2a2a2e")
chars.wear(NAME, "bomb_hat")
print(chars.export(NAME)["tris"])
roblox.export_char(NAME)
