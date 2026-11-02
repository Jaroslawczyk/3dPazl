"""Roblox package of the shop: GLB in studs (1 stud = 0.28 m), textures <= 1024 px, split PBR maps for SurfaceAppearance.
Run after gen_car_boat_shop.py:  .venv/Scripts/python.exe scripts/export_roblox.py"""
import pathlib, numpy as np, trimesh as tm
from PIL import Image
SRC = pathlib.Path("projects/car_boat_shop/export/car_boat_shop.glb"); OUT = pathlib.Path("projects/car_boat_shop/roblox")
(OUT / "textures").mkdir(parents=True, exist_ok=True)
S = 1 / 0.28
sc = tm.load(SRC)
b = sc.bounds; sc.apply_translation([-(b[0][0] + b[1][0]) / 2, -b[0][1], -(b[0][2] + b[1][2]) / 2])   # pivot: floor centre
sc.apply_scale(S)
def fit(im, mx=1024):
    k = min(1.0, mx / max(im.size)); return im if k == 1 else im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
rows = []
for name, g in sc.geometry.items():
    m = g.visual.material
    base = fit(m.baseColorTexture.convert("RGB")); m.baseColorTexture = base
    if m.normalTexture is not None: m.normalTexture = fit(m.normalTexture.convert("RGB"))
    orm = None
    if m.metallicRoughnessTexture is not None:
        orm = fit(m.metallicRoughnessTexture.convert("RGB")); m.metallicRoughnessTexture = orm; m.occlusionTexture = orm
    col = base.copy()
    if name.startswith("glass"): col = col.convert("RGBA"); col.putalpha(140)            # Roblox: alpha in ColorMap
    col.save(OUT / "textures" / f"{name}_color.png")
    if m.normalTexture is not None: m.normalTexture.save(OUT / "textures" / f"{name}_normal.png")
    if orm is not None:
        r, gch, bch = orm.split()
        gch.save(OUT / "textures" / f"{name}_roughness.png"); bch.save(OUT / "textures" / f"{name}_metalness.png")
    rows.append((name, base.size, m.normalTexture is not None, orm is not None))
sc.export(OUT / "tech_shop_roblox.glb")
bb = sc.bounds; size = (bb[1] - bb[0]).round(1)
(OUT / "README.txt").write_text(f"""Магазин для Roblox Studio
Файл: tech_shop_roblox.glb  (в студах: 1 stud = 0.28 м), размер {size[0]} x {size[2]} x {size[1]} studs (ширина x глубина x высота), центр на полу.

Импорт: Roblox Studio -> вкладка Avatar/Home -> Import 3D (или Asset Manager -> Bulk Import) -> выбрать tech_shop_roblox.glb.
В окне импорта оставить Scale = 1, включить Import Textures (карты уже в файле).
Получится Model из MeshPart по одному на материал ({len(rows)} шт.) с SurfaceAppearance.

После импорта:
 1. Стекло (MeshPart 'glass...'): в SurfaceAppearance поставить AlphaMode = Transparency (альфа 140/255 уже в glass_color.png).
 2. Выделить все части -> Anchored = true, CanCollide = true; стекло и ящики с цветами можно CanCollide = false.
 3. Проём входа открыт; дверей нет.
Если рельеф нормалей выглядит вывернутым - повернуть зелёный канал (в textures/*_normal.png инвертировать G).

textures/ - те же карты по отдельности (color / normal / roughness / metalness) для ручной загрузки в SurfaceAppearance.
Ограничения Roblox: текстуры <= 1024 px (учтено), у меша <= 21 844 треугольников (здесь {len(sc.dump(concatenate=True).faces)}).
""", encoding="utf-8")
print(size, len(rows), "materials,", len(sc.dump(concatenate=True).faces), "tris")
