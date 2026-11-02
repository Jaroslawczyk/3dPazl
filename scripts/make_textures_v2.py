"""Second texture set for the shop: red-orange brick walls, green fish-scale roof, wood-plank floor.
Seamless 512 px maps (colour, normal, rough, metal, ao, orm) -> textures/car_boat_shop. Run with .venv/Scripts/python.exe"""
import pathlib, numpy as np
from PIL import Image, ImageDraw
OUT = pathlib.Path("textures/car_boat_shop"); N = 512; rng = np.random.default_rng(11)
def blur(a, k=1):
    for _ in range(k): a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a
def save(name, col, height, k, rough, ao_str):
    h = (height - height.min()) / (np.ptp(height) + 1e-9)
    dx = np.roll(h, -1, 1) - np.roll(h, 1, 1); dy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    n = np.stack([-dx * k * 4, dy * k * 4, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    nrm = ((n * .5 + .5) * 255).astype(np.uint8)
    ao = np.clip(1 - ao_str * (blur(h, 3) - h).clip(0, None) * 6, 0.55, 1)
    g = lambda a: Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    rg = np.full((N, N), rough) + (blur(h, 1) - .5) * .1
    Image.fromarray(col.astype(np.uint8)).save(OUT / f"{name}.png"); Image.fromarray(nrm).save(OUT / f"{name}_normal.png")
    g(rg).convert("RGB").save(OUT / f"{name}_rough.png"); g(np.zeros((N, N))).convert("RGB").save(OUT / f"{name}_metal.png")
    g(ao).convert("RGB").save(OUT / f"{name}_ao.png")
    Image.fromarray(np.stack([g(ao), g(rg), g(np.zeros((N, N)))], -1).reshape(N, N, 3) if False else
                    np.stack([np.asarray(g(ao)), np.asarray(g(rg)), np.zeros((N, N), np.uint8)], -1)).save(OUT / f"{name}_orm.png")
# --- brick: 8 rows x 4 bricks (0.5 x 0.25 m on a 2 m tile)
bh, bw, mort = 64, 128, 6
col = np.zeros((N, N, 3)); hgt = np.zeros((N, N))
y, x = np.mgrid[0:N, 0:N]
row = y // bh; xs = (x + (bw // 2) * (row % 2)) % N; bid = (xs // bw) + row * 4
tone = rng.random(32)[bid % 32]
inb = ((y % bh) >= mort // 2) & ((y % bh) < bh - mort // 2) & ((xs % bw) >= mort // 2) & ((xs % bw) < bw - mort // 2)
base = np.array([224, 98, 62.]); alt = np.array([240, 140, 80.])
brick = base[None, None] * (1 - tone[..., None]) + alt[None, None] * tone[..., None]
brick *= (0.93 + blur(rng.random((N, N)), 2)[..., None] * .25)
col = np.where(inb[..., None], brick, np.array([236, 226, 205.])[None, None])
hgt = np.where(inb, 1.0, 0.0) + blur(rng.random((N, N)), 1) * .15
save("wall_brick", col, hgt, 3.0, 0.85, 1.0)
# --- fish-scale shingles
im = Image.new("RGB", (N, N), "#1b4d33"); hm = Image.new("L", (N, N), 0)
d, dh = ImageDraw.Draw(im), ImageDraw.Draw(hm)
rw, rh = 64, 32
for r in range(-1, N // rh + 2):
    for c in range(-1, N // rw + 2):
        cx = c * rw + (rw // 2 if r % 2 else 0); cy = r * rh
        t = rng.random(); shade = (int(48 + 30 * t), int(104 + 40 * t), int(78 + 26 * t))
        for ox in (0, -N, N):
            for oy in (0, -N, N):
                bb = [cx - rw // 2 + ox, cy - rh + oy, cx + rw // 2 + ox, cy + rh + oy]
                d.pieslice(bb, 0, 180, fill=shade, outline=(20, 90, 50), width=3) if False else d.ellipse([bb[0], bb[1] - rh, bb[2], bb[3]], fill=shade, outline=(24, 62, 46), width=3)
                dh.ellipse([bb[0], bb[1] - rh, bb[2], bb[3]], fill=int(120 + 100 * (r % 7) / 7), outline=40, width=3)
col = np.asarray(im, float) * (0.95 + blur(rng.random((N, N)), 2)[..., None] * .1)
save("roof_shingles", col, np.asarray(hm, float) + blur(rng.random((N, N)), 1) * 10, 3.0, 0.75, 1.0)
# --- wood planks floor: 4 planks of 128 px, joints staggered
y, x = np.mgrid[0:N, 0:N]; prow = y // 128; xs = (x + prow * 170) % N
pid = prow * 2 + xs // 256; tone = rng.random(16)[pid % 16]
grain = np.sin((y * 0.12 + blur(rng.random((N, N)), 6) * 40 + tone * 30)) * .5 + .5
base = np.array([210, 150, 85.]); dark = np.array([160, 100, 50.])
col = base[None, None] * (1 - grain[..., None] * .35) + dark[None, None] * (grain[..., None] * .35)
col *= (0.9 + tone[..., None] * .2)
seam = ((y % 128) < 3) | ((xs % 256) < 3); col = np.where(seam[..., None], col * .45, col)
save("floor_planks", col, np.where(seam, 0, 1.0) + grain * .1, 2.0, 0.5, 1.0)
print("ok")
