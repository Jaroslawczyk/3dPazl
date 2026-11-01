"""One-off: add years / regions / palette to style YAMLs (kept as a script so the data is easy to edit and re-apply)."""
from pathlib import Path

import yaml

META = {  # id: (years, regions, facade palette [walls...], trims, roofs)
    "generic": ([-4000, 2100], ["global"], ["#e8e4da", "#d9c7a4", "#c9d3d6"], ["#f4f2ec"], ["#8a4a35", "#5a5d64"]),
    "greek": ([-700, -30], ["mediterranean"], ["#efe9dd", "#e6dccb"], ["#f6f1e7"], ["#a85a3a"]),
    "roman": ([-500, 500], ["mediterranean", "europe_west"], ["#e2d6c2", "#d8b98f"], ["#f3eee4"], ["#a35a3a"]),
    "romanesque": ([1000, 1200], ["europe_west"], ["#d8c39c", "#cdbb98", "#bba98a"], ["#e3d5b8"], ["#9a5638", "#5f5e60"]),
    "gothic": ([1140, 1520], ["europe_west", "europe_north"], ["#c9c0ad", "#a8553f", "#bdb6a7"], ["#e2dccd"], ["#6b7076", "#4d5258"]),
    "renaissance": ([1400, 1600], ["europe_west", "mediterranean"], ["#e3c38a", "#d9a679", "#e9d9b8", "#c98f6a"], ["#f2ead8"], ["#a65f3d"]),
    "baroque": ([1600, 1750], ["europe_west", "europe_east", "russia"], ["#e9b9a9", "#a8c8dd", "#efd27c", "#b6d4b4", "#f0e2c8"], ["#ffffff", "#f6f0e2"], ["#5f9d82", "#6a6f75"]),
    "classicism": ([1750, 1850], ["europe_west", "russia"], ["#efd27c", "#e7c8a0", "#d7dde0", "#efe1c4"], ["#ffffff"], ["#4f7f68", "#7c8288"]),
    "russian_orthodox": ([988, 1917], ["russia", "europe_east"], ["#f4f1ea", "#e7c96d", "#d7e5ee", "#f1d6d0"], ["#ffffff"], ["#3f7a5c", "#1f4f8c", "#c9a227"]),
    "russian_wooden": ([900, 1950], ["russia"], ["#9c7048", "#7d5a3c", "#b38a5d"], ["#f2ece0", "#5c86a8", "#3f7a5c"], ["#6f5a46", "#4a6d58"]),
    "lithuanian": ([1600, 1950], ["europe_east", "europe_north"], ["#7f9b74", "#b88a5b", "#6d7f95", "#a64f3e"], ["#ffffff"], ["#6b5a48", "#4f5258"]),
    "german_fachwerk": ([1400, 1800], ["europe_west"], ["#f4efe4", "#efe1c0", "#e9d3c8"], ["#3a2a20", "#6b2e22"], ["#9c4a32", "#5b4a44"]),
    "medieval_castle": ([1000, 1500], ["europe_west", "europe_north", "europe_east"], ["#9e978c", "#8a8378", "#b1a896"], ["#c9c1b2"], ["#4f5459", "#7a4a36"]),
    "dugout": ([-3000, 1950], ["europe_east", "russia"], ["#6d5440"], ["#5a4634"], ["#5d6f3f"]),
    "soviet_panel": ([1956, 1991], ["russia", "europe_east", "central_asia"], ["#c9c6bd", "#d8cfb9", "#b9c4c9", "#d9b8a2", "#e3e0d4"], ["#9aa0a2", "#7d8a96"], ["#404245"]),
    "stalinist": ([1933, 1955], ["russia", "europe_east"], ["#e3c38a", "#d9b48f", "#e8d6b0", "#c98f6a"], ["#f4efe4"], ["#8c3b30", "#5d6066"]),
    "constructivism": ([1920, 1960], ["russia", "europe_west"], ["#f2f0ea", "#d7d3c8", "#c9563c"], ["#3a3a3a"], ["#3c3c3c"]),
    "modern": ([1970, 2100], ["global"], ["#c7cdd2", "#e7e5df", "#6c7a86", "#2f3b45"], ["#a9b0b6"], ["#3a3c40"]),
    "egyptian": ([-3000, -30], ["north_africa"], ["#d9bf8c", "#cfae76"], ["#e8d3a5", "#2f6ea8"], ["#d2b783"]),
    "mesopotamian": ([-3500, -500], ["middle_east"], ["#c4a27a", "#b8946c"], ["#2a5fa6", "#d8b44a"], ["#b08e66"]),
    "mesoamerican": ([-1000, 1521], ["americas"], ["#cfc6ad", "#b8452f", "#d8cfb8"], ["#2f8a7a", "#c9a227"], ["#c8bfa6"]),
    "byzantine": ([330, 1453], ["mediterranean", "europe_east"], ["#a8553f", "#b8664c", "#d9c7a4"], ["#e3d9c4"], ["#7a7f86", "#a65f3d"]),
    "caucasian": ([300, 1700], ["caucasus"], ["#c98e78", "#d9b49a", "#b9a48c"], ["#e3cdb8"], ["#b98c74"]),
    "ottoman": ([1300, 1922], ["middle_east", "europe_east", "mediterranean"], ["#e7e0d0", "#d8cdb6"], ["#2f6e9e", "#f4efe4"], ["#7a8188"]),
    "persian": ([1000, 1800], ["middle_east", "central_asia"], ["#d8b27a", "#c99e66"], ["#1f6fa8", "#38a3b8", "#f2e6c8"], ["#2a74b8", "#3aa6b9"]),
    "moorish": ([711, 1492], ["mediterranean", "north_africa"], ["#ead8b4", "#f4efe4", "#d6a978"], ["#2f6e9e", "#3f8a5c"], ["#a65f3d", "#3f8a5c"]),
    "mughal": ([1526, 1857], ["south_asia"], ["#f4f1ea", "#b0533b"], ["#b0533b", "#f4f1ea"], ["#f4f1ea"]),
    "hindu": ([500, 1700], ["south_asia"], ["#d9b27a", "#c98f6a", "#e8d3a5"], ["#c9a227"], ["#c98f6a"]),
    "chinese": ([-200, 1912], ["east_asia"], ["#a6312a", "#8e2a24", "#e7ddc8"], ["#2f7a6a", "#c9a227"], ["#d8a428", "#4f5a5e", "#2f7a52"]),
    "japanese": ([600, 1900], ["east_asia"], ["#f2ede2", "#4a3527"], ["#3a2a20"], ["#3e4247", "#5a4a3a"]),
    "scandinavian": ([1100, 1900], ["europe_north"], ["#3a2a20", "#8e2a24", "#d9c79c", "#f2ede2"], ["#f4f1ea"], ["#5d6f3f", "#4f4440"]),
    "dutch": ([1500, 1800], ["europe_west", "europe_north"], ["#8e3b2b", "#a85a3f", "#6e2f24", "#c98f6a"], ["#ffffff"], ["#4a3a36", "#6b3f30"]),
    "victorian": ([1837, 1910], ["europe_west", "americas"], ["#d9c79c", "#9bb5c4", "#c98f8a", "#a4b98a", "#e8dcc4"], ["#ffffff", "#5d2a3a"], ["#4f5459", "#6b3f30"]),
    "alpine": ([1600, 2100], ["europe_west"], ["#9c7048", "#b38a5d"], ["#f4f1ea", "#3f7a5c", "#8e2a24"], ["#5a4a3a"]),
    "art_deco": ([1920, 1940], ["americas", "europe_west", "global"], ["#e3d9c4", "#d7c7a4", "#c9c3b8"], ["#c9a227", "#3a3a3a"], ["#3a3a3a"]),
    "brutalism": ([1950, 1985], ["global", "russia"], ["#a3a29c", "#b4b2aa", "#8f8e88"], ["#6f6e69"], ["#3c3c3c"]),
    "industrial": ([1800, 2100], ["global"], ["#8e3b2b", "#a85a3f", "#9aa0a2"], ["#d9b27a", "#3a3a3a"], ["#3c3c3c", "#6b7074"]),
    "military": ([1900, 2100], ["global"], ["#9a9a8e", "#7d8270", "#a39e8c"], ["#5f6356"], ["#6d7a4f"]),
}

DIR = Path(__file__).resolve().parent.parent / "pazl" / "styles"
for sid, (years, regions, walls, trims, roofs) in META.items():
    f = DIR / f"{sid}.yaml"
    d = yaml.safe_load(f.read_text("utf-8"))
    d["years"] = years
    d["regions"] = regions
    d["palette"] = {"wall": walls, "trim": trims, "roof": roofs}
    f.write_text(yaml.safe_dump(d, allow_unicode=True, sort_keys=False), "utf-8")
print("updated", len(META))
