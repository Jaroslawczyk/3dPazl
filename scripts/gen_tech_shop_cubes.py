"""Tech shop built from 1 m cubes (voxel/brick look), 8x6 footprint. x right, y back, z up; front = y 0."""
import json, pathlib
V = {}
def c(x, y, z, col): V[(x, y, z)] = col
def fill(xs, ys, zs, col):
    for x in xs:
        for y in ys:
            for z in zs: c(x, y, z, col)
W, D = 8, 6
WALL, RED, WHITE, DARK, GLASS = "#e8e4da", "#d8262c", "#f5f5f5", "#1c1e24", "#8fd3f4"
fill(range(-2, W+2), range(-3, D+1), [0], "#7d8590")            # pavement + floor
fill(range(W), range(D), [0], "#b9a98d")
for z in (1, 2, 3):                                              # walls
    for x in range(W):
        c(x, D-1, z, WALL)
        c(x, 0, z, WALL)
    for y in range(D):
        c(0, y, z, WALL); c(W-1, y, z, WALL)
for x in (3, 4):                                                 # door
    for z in (1, 2): V.pop((x, 0, z), None)
for x in (1, 2, 5, 6): c(x, 0, 2, GLASS)                         # windows
for x in (1, 2, 5, 6): c(x, 0, 3, WALL)
fill(range(W), range(D), [4], "#4a4f5c")                         # roof
for x in range(W):                                               # crenellated parapet
    for y in range(D):
        if (x in (0, W-1) or y in (0, D-1)) and (x+y) % 2 == 0: c(x, y, 5, WALL)
for x in range(1, 7): c(x, 0, 5, RED); c(x, 0, 6, RED if x % 2 else WHITE)   # sign
c(2, 3, 5, "#c9ced6"); c(3, 3, 5, "#c9ced6"); c(6, 4, 5, DARK); c(6, 4, 6, "#e0e0e0")  # AC, dish
for x in range(1, 7): c(x, -1, 3, RED if x % 2 else WHITE)       # awning
for x in range(1, 7):                                            # shelves with TVs
    c(x, D-2, 1, "#5b4636")
    c(x, D-2, 2, DARK if x % 2 else "#3fa7ff")
fill([5, 6], [3], [1], "#3b4252"); c(6, 3, 2, DARK)              # counter + register
fill([1], [1, 2], [1], WHITE); fill([1], [1, 2], [2], "#6ab7e8") # washers
c(1, 3, 1, "#dfe6ee"); c(1, 3, 2, "#dfe6ee")                     # fridge
c(3, 2, 1, "#c8b79a"); c(4, 2, 1, "#c8b79a")                     # table
c(-2, -1, 1, "#2b2f3a"); c(-2, -1, 2, "#3fa7ff")                 # street TV
c(9, -1, 1, "#6b4f35")                                           # bench
E = [{"id": f"c{x}_{y}_{z}", "type": "box", "at": [x+0.5-W/2, y+0.5-D/2], "offset": [0, 0, z],
      "params": {"w": 1, "d": 1, "h": 1}, "colors": {"wall": col}} for (x, y, z), col in sorted(V.items())]
r = {"name": "tech_shop_cubes", "style": "blocky_toy", "detail": "lowpoly", "elements": E}
p = pathlib.Path("projects/tech_shop_cubes"); p.mkdir(exist_ok=True)
(p/"recipe.json").write_text(json.dumps(r), encoding="utf-8"); print(len(E), "cubes")
