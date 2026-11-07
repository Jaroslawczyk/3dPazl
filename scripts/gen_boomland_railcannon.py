"""Boomland rail cannon (v1.133): three separate models so the wheels can really turn on the rails.
Drawn in Roblox studs (front = +Z, barrel looks +Z; the importer turns it to -Z). Run:
.venv/Scripts/python.exe scripts/gen_boomland_railcannon.py -> projects/boomland_world/export/railcannon_*.glb
  railcannon_body  : carriage 6.4 x 10.4, deck top at y 2.2 (wheel centres at x +-2.6, z +-2.2/+-3.6, y 0.8 over the rail)
  railcannon_wheel : one flanged wheel, axle along X, radius 0.8, centre at the origin
  railcannon_head  : turret ring + shield + barrel, pivot at its bottom centre"""
import sys
sys.path.insert(0, "scripts")
import trimesh as tm
from boomland_kit import box, boxc, cyl, cylx, col, export

YEL, NAVY, METAL, METAL_D, WOOD, RED, LAMP = "#f2b632", "#2b2f3a", "#5a606c", "#22252c", "#9a6a40", "#d93a32", "#ffe28c"

# ---- body
for z in (-2.9, 2.9):                                   # two bogies (frame between the wheels)
    box(-3.0, .55, z - 1.3, 3.0, 1.15, z + 1.3, METAL_D)
    for x in (-2.6, 2.6):
        box(x - .35, .5, z - 1.5, x + .35, 1.1, z + 1.5, METAL)     # side frames over the wheels
box(-2.2, 1.15, -4.6, 2.2, 1.6, 4.6, NAVY)               # chassis beam
box(-3.2, 1.6, -5.2, 3.2, 2.2, 5.2, YEL)                  # deck
for z in (-5.2, 5.2):                                    # buffers
    for x in (-2.0, 2.0):
        s = 1 if z > 0 else -1
        box(x - .25, 1.15, min(z, z + s * .5), x + .25, 1.65, max(z, z + s * .5), METAL_D)   # buffer rod
        box(x - .45, 1.0, min(z + s * .5, z + s * .75), x + .45, 1.8, max(z + s * .5, z + s * .75), RED)  # buffer plate
for x in (-3.0, 3.0):                                    # side railings at the back half
    for z in (.8, 2.8, 4.8):
        box(x - .08, 2.2, z - .08, x + .08, 3.4, z + .08, NAVY)
    box(x - .1, 3.3, .7, x + .1, 3.5, 4.9, YEL)
for i in range(4):                                       # ladder on the right side
    box(3.2, .6 + i * .45, 3.3, 3.5, .7 + i * .45, 4.5, METAL)
box(3.2, .5, 3.25, 3.55, 2.2, 3.35, METAL); box(3.2, .5, 4.45, 3.55, 2.2, 4.55, METAL)
box(-1.0, 2.2, 3.4, 1.0, 2.8, 4.6, WOOD); box(-1.0, 2.8, 4.4, 1.0, 3.9, 4.6, WOOD)   # gunner bench
for x in (-2.8, 2.8):
    cyl(x, 2.2, 2.5, -4.9, .25, LAMP, 8)                 # front lamps
export("railcannon_body")

# ---- wheel (axle X): rim, flange on the inside, hub and four spokes so the turning shows
cylx(-.22, .22, 0, 0, .8, METAL_D, 16)
cylx(-.3, -.22, 0, 0, .95, METAL, 16)
cylx(-.26, .28, 0, 0, .25, YEL, 10)
for a in (0, 1):
    boxc(.24, 0, 0, .06, 1.3 if a == 0 else .18, .18 if a == 0 else 1.3, YEL)
export("railcannon_wheel")

# ---- head: turret ring, gun shield, barrel along +Z
cyl(0, 0, .5, 0, 1.8, NAVY, 16)
cyl(0, .5, .8, 0, 1.6, YEL, 16)
box(-1.3, .8, -1.0, 1.3, 2.0, .8, YEL)                    # mount
box(-1.7, .8, .8, 1.7, 2.6, 1.1, NAVY)                    # shield
box(-1.7, 2.6, .5, 1.7, 2.8, 1.1, YEL)
def cylz(z0, z1, y, r, c, n=14):
    m = tm.creation.cylinder(radius=r, height=z1 - z0, sections=n); m.apply_translation([0, y, (z0 + z1) / 2]); return col(m, c)
cylz(-.6, 5.2, 1.7, .45, METAL_D)                         # barrel
cylz(4.6, 5.5, 1.7, .6, NAVY)                             # muzzle ring
cylz(-1.3, -.6, 1.7, .65, METAL)                          # breech
export("railcannon_head")
