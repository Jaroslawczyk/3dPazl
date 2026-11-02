"""Roblox-style electronics shop as a pazl box recipe (x right, y back, z up; front = -Y)."""
import json, pathlib
E = []
def b(i, x, y, z, w, d, h, c):
    E.append({"id": i, "type": "box", "at": [round(x,3), round(y,3)], "offset": [0, 0, round(z,3)],
              "params": {"w": w, "d": d, "h": h}, "colors": {"wall": c}})
WALL, TRIM, GLASS, DARK = "#e8e4da", "#2b2f3a", "#8fd3f4", "#1c1e24"
RED, WHITE = "#d8262c", "#f5f5f5"
b("ground", 0, -1.5, 0, 18, 16, 0.2, "#7d8590")        # pavement
b("floor", 0, 0, 0.2, 12, 9, 0.2, "#b9a98d")           # shop floor
Z0, H = 0.4, 4.0
b("wall_back", 0, 4.35, Z0, 12, 0.3, H, WALL)
b("wall_l", -5.85, 0, Z0, 0.3, 9, H, WALL)
b("wall_r", 5.85, 0, Z0, 0.3, 9, H, WALL)
FY = -4.35
b("f_top", 0, FY, Z0+3.3, 12, 0.3, 0.7, WALL)
b("f_pier_l", -5.5, FY, Z0, 1.0, 0.3, 3.3, WALL)
b("f_pier_r", 5.5, FY, Z0, 1.0, 0.3, 3.3, WALL)
b("f_pier_c", 0, FY, Z0+2.6, 2.0, 0.3, 0.7, WALL)       # above door
for s, x in (("l", -3), ("r", 3)):
    b(f"f_sill_{s}", x, FY, Z0, 4, 0.3, 0.9, WALL)
    b(f"glass_{s}", x, FY, Z0+0.9, 4, 0.08, 2.4, GLASS)
    for k, dx in enumerate((-2, 0, 2)):
        b(f"mull_{s}{k}", x+dx, FY-0.05, Z0+0.9, 0.1, 0.12, 2.4, TRIM)
    b(f"fr_top_{s}", x, FY-0.05, Z0+3.25, 4, 0.12, 0.1, TRIM)
    b(f"fr_bot_{s}", x, FY-0.05, Z0+0.85, 4, 0.12, 0.1, TRIM)
b("door_fr_l", -1.0, FY-0.05, Z0, 0.12, 0.14, 3.0, TRIM)
b("door_fr_r", 1.0, FY-0.05, Z0, 0.12, 0.14, 3.0, TRIM)
b("door_fr_t", 0, FY-0.05, Z0+2.9, 2.1, 0.14, 0.12, TRIM)
b("door_mat", 0, FY-0.9, 0.2, 1.8, 1.0, 0.04, "#3a3f4b")
# roof, parapet
b("roof", 0, 0, Z0+H, 12.6, 9.6, 0.3, "#4a4f5c")
b("par_f", 0, -4.75, Z0+H+0.3, 12.6, 0.2, 0.5, WALL)
b("par_b", 0, 4.75, Z0+H+0.3, 12.6, 0.2, 0.5, WALL)
b("par_l", -6.2, 0, Z0+H+0.3, 0.2, 9.6, 0.5, WALL)
b("par_r", 6.2, 0, Z0+H+0.3, 0.2, 9.6, 0.5, WALL)
# sign
b("sign", 0, -4.65, Z0+H+0.1, 8.4, 0.35, 1.5, RED)
b("sign_plate", 0, -4.85, Z0+H+0.25, 7.6, 0.06, 1.2, WHITE)
for k in range(5):  # stylised "letters"
    b(f"sign_l{k}", -2.8+k*1.4, -4.9, Z0+H+0.45, 0.9, 0.05, 0.8, RED)
b("sign_pc", -3.6, -4.9, Z0+H+0.6, 0.0001+0.05, 0.05, 0.05, RED) if False else None
# awning (7 stripes)
for k in range(7):
    b(f"awn{k}", -5.4+k*1.8, -5.3, Z0+3.0, 1.8, 1.7, 0.15, RED if k % 2 == 0 else WHITE)
b("awn_valance", 0, -6.15, Z0+2.7, 12.6, 0.08, 0.45, RED)
# rooftop gear
b("ac1", -3.5, 2, Z0+H+0.3, 1.8, 1.2, 0.9, "#c9ced6")
b("ac2", -1.2, 2, Z0+H+0.3, 1.8, 1.2, 0.9, "#c9ced6")
b("dish_base", 3.5, 2, Z0+H+0.3, 0.3, 0.3, 1.6, DARK)
b("dish", 3.5, 2, Z0+H+1.7, 1.4, 0.2, 1.4, "#e0e0e0")
# interior: shelf units on back wall with TVs
for s in range(3):
    x = -3.8 + s*3.8
    b(f"shelf{s}", x, 3.8, 0.4, 3.2, 0.7, 2.6, "#5b4636")
    for lvl in range(3):
        z = 0.55 + lvl*0.85
        b(f"shelfb{s}{lvl}", x, 3.8, z+0.7, 3.0, 0.72, 0.06, "#8a6a4a")
        for k in range(3):
            b(f"tv{s}{lvl}{k}", x-1.0+k*1.0, 3.4, z+0.06, 0.8, 0.12, 0.55, DARK)
            b(f"scr{s}{lvl}{k}", x-1.0+k*1.0, 3.33, z+0.1, 0.7, 0.03, 0.45, ["#3fa7ff","#ffb02e","#58d68d"][(s+lvl+k)%3])
# left: white goods row
for k, x in enumerate((-5.0, -3.9, -2.8)):
    b(f"wm{k}", x, -1.0, 0.4, 0.95, 0.9, 1.15, WHITE)
    b(f"wmd{k}", x, -1.47, 0.9, 0.5, 0.05, 0.5, "#6ab7e8")
b("fridge1", -5.2, 1.5, 0.4, 1.0, 0.9, 2.2, "#dfe6ee")
b("fridge2", -4.1, 1.5, 0.4, 1.0, 0.9, 2.0, "#cfd8e2")
# counter + register
b("counter", 3.6, 0.8, 0.4, 3.6, 1.0, 1.1, "#3b4252")
b("counter_top", 3.6, 0.8, 1.5, 3.8, 1.2, 0.08, "#d8dee9")
b("register", 4.4, 0.8, 1.58, 0.7, 0.5, 0.45, DARK)
# centre display tables with phones/laptops
for k, x in enumerate((-0.8, 1.2)):
    b(f"table{k}", x, -1.8, 0.4, 1.8, 1.0, 0.9, "#c8b79a")
    b(f"laptop_b{k}", x, -1.8, 1.3, 0.7, 0.5, 0.04, "#9aa0ab")
    b(f"laptop_s{k}", x, -1.6, 1.34, 0.7, 0.04, 0.45, DARK)
# outside: street TV stand + bench
b("stand", -8, -3.5, 0.2, 0.6, 0.6, 1.2, TRIM)
b("stand_tv", -8, -3.5, 1.4, 1.6, 0.12, 0.95, DARK)
b("stand_scr", -8, -3.58, 1.47, 1.45, 0.06, 0.8, "#3fa7ff")
b("bench", 8, -3.5, 0.2, 1.8, 0.5, 0.5, "#6b4f35")
r = {"name": "tech_shop", "style": "blocky_toy", "detail": "lowpoly", "elements": E}
pathlib.Path("projects/tech_shop/recipe.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
print(len(E), "elements")
