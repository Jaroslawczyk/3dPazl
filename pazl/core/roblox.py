"""Export for Roblox: everything lands in projects/roblox/<name>/ with a README of upload steps.
Classic Shirt/Pants: 585x559 PNG on the official template (regions measured from Roblox's own template files).
Animations: KeyframeSequence .rbxmx for an R6 rig. Models, accessories: GLB for the Studio 3D Importer. Images: PNG up to 1024.
Formats: docs/ROBLOX.md."""
from __future__ import annotations

import re
import shutil
import xml.sax.saxutils as sx
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

from ..paths import PROJECTS
from . import chars, rig, skins
from .chars import body, cloth
from .chars.field import decimate
from .rig import anim, skeleton

OUT = PROJECTS / "roblox"
SIZE = (585, 559)
# x, y, w, h of each face on the official template; the left arm/leg block and the right one share the same order
TORSO = {"up": (231, 8, 128, 64), "front": (231, 74, 128, 128), "down": (231, 204, 128, 64), "side1": (165, 74, 64, 128),
         "side2": (361, 74, 64, 128), "back": (427, 74, 128, 128)}
LIMBS = [{"up": (217, 289, 64, 64), "down": (217, 485, 64, 64), "sides": [(19, 355), (85, 355), (151, 355), (217, 355)]},
         {"up": (308, 289, 64, 64), "down": (308, 485, 64, 64), "sides": [(308, 355), (374, 355), (440, 355), (506, 355)]}]
# garment -> which template it paints: limb = share of the arm/leg length from the top, torso = share from the top/bottom
CLASSIC = {"tshirt": ("shirt", .5, 1), "longsleeve": ("shirt", 1, 1), "tank": ("shirt", 0, 1), "jacket": ("shirt", 1, 1), "dress": ("shirt", 0, 1),
           "cloak": ("shirt", 0, 0), "gloves": ("shirt", -.14, 0),
           "pants": ("pants", 1, .22), "shorts": ("pants", .55, .22), "skirt": ("pants", .5, .3), "boots": ("pants", -.35, 0), "shoes": ("pants", -.14, 0)}
ACCESSORY = ("bird", "bomb_hat", "hair_spiky", "beanie_back", "acc_head", "acc_chest", "hat", "beanie", "hair_short", "hair_long", "beard", "scarf", "belt")
MESH_TRIS, ACC_TRIS, IMG_MAX = 20000, 4000, 1024


def _safe(n):
    return re.sub(r"[^\w\-]+", "_", n or "model").strip("_") or "model"


# ------------------------------------------------------------------ classic clothing
def _swatch(g, o, H):
    """RGBA tile painted with the garment's skin or colour; pattern scale follows the character (64 px = 1 stud)."""
    s = g.get("skin") or (None if g.get("color") else o.get("skin"))
    if not s:
        return np.array([*(body.rgb(g.get("color") or o["color"]) * 255), 255], np.uint8)[None, None]
    s = skins.resolve(s)
    px = int(np.clip(float(s.get("tile", .3)) / (H / 5) * 64, 16, 256))
    a = np.asarray(skins.tile_image(s).convert("RGB").resize((px, px)))
    return np.dstack([a, np.full(a.shape[:2], 255, np.uint8)])


def _paint(im, box, tile, frm=0.0, to=1.0):
    """Fill the band frm..to (from the top) of a template box."""
    x, y, w, h = box
    y0, y1 = y + int(round(h * frm)), y + int(round(h * to))
    if y1 <= y0:
        return
    im[y0:y1, x:x + w] = np.tile(tile, ((y1 - y0) // tile.shape[0] + 1, w // tile.shape[1] + 1, 1))[:y1 - y0, :w]


def classic(outfit, template, H):
    """{'shirt': array, 'pants': array}: the outfit drawn on the official templates, empty areas transparent."""
    res = {}
    for g in outfit:
        if g["kind"] not in CLASSIC:
            continue
        which, limb, torso = CLASSIC[g["kind"]]
        im = res.setdefault(which, np.zeros((SIZE[1], SIZE[0], 4), np.uint8))
        t = _swatch(g, cloth.kinds_for(template)[g["kind"]][2], H)
        if torso:
            for k, b in TORSO.items():
                if which == "shirt" or k == "down":
                    _paint(im, b, t, 0, torso if which == "shirt" else 1)
                elif k in ("front", "back", "side1", "side2"):
                    _paint(im, b, t, 1 - torso, 1)
        for L in LIMBS:
            for x, y in L["sides"]:
                if limb > 0:
                    _paint(im, (x, y, 64, 128), t, 0, limb)
                elif limb < 0:
                    _paint(im, (x, y, 64, 128), t, 1 + limb, 1)
            if limb < 0 or limb >= 1:
                _paint(im, L["down"], t)
            if limb > 0:
                _paint(im, L["up"], t)
        if g.get("print") and which == "shirt":  # picture in the middle of the torso front
            x, y, w, h = TORSO["front"]
            k = int(w * float(g.get("print_size", .78)))
            pic = np.asarray(Image.open(PROJECTS / g["print"]).convert("RGBA").resize((k, k), Image.LANCZOS)).astype(float)
            x0, y0 = x + (w - k) // 2, y + int(h * .52) - k // 2
            a = pic[..., 3:] / 255
            box = im[y0:y0 + k, x0:x0 + k]
            box[..., :3] = (pic[..., :3] * a + box[..., :3] * (1 - a)).astype(np.uint8)
            box[..., 3] = np.maximum(box[..., 3], pic[..., 3].astype(np.uint8))
        if g["kind"] == "jacket":  # zip down the front
            x, y, w, h = TORSO["front"]
            im[y:y + h, x + w // 2 - 2:x + w // 2 + 2] = (40, 40, 44, 255)
    return res


# ------------------------------------------------------------------ R6 animation
A_SIDE = {"R": np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0.]]), "L": np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0.]])}
A_MID = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0.]])
S = np.diag([-1., 1, -1])  # our characters face +Z, Roblox ones face -Z
ARM_REST = {"L": np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1.]]), "R": np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.]])}  # lowered arm -> T-pose


def _cf(R, t=(0, 0, 0)):
    v = [*t, *np.asarray(R).ravel()]
    tags = ("X", "Y", "Z", "R00", "R01", "R02", "R10", "R11", "R12", "R20", "R21", "R22")
    return '<CoordinateFrame name="CFrame">' + "".join(f"<{k}>{float(x):.6f}</{k}>" for k, x in zip(tags, v)) + "</CoordinateFrame>"


def _pose(name, R, t=(0, 0, 0), kids="", weight=1):
    return (f'<Item class="Pose"><Properties>{_cf(R, t)}<token name="EasingDirection">0</token><token name="EasingStyle">0</token>'
            f'<string name="Name">{sx.escape(name)}</string><float name="Weight">{weight}</float></Properties>{kids}</Item>')


def r6_poses(bones, clip, f):
    """Pose values of one frame: name -> Motor6D rotation; plus torso offset in studs."""
    names, par, heads, tails = skeleton.order(bones)
    rots, rt = anim.sample(clip, names, f)
    R, P = anim.fk(par, heads, rots, rt)
    ix = {n: i for i, n in enumerate(names)}
    conv = lambda M: S @ M @ S  # noqa: E731
    torso = conv(R[ix["hips"]])
    H = float(np.max(tails[:, 1]))
    off = S @ (P[ix["hips"]] - heads[ix["hips"]]) / (H / 5)
    off[2] = off[0] = 0  # in place: the Humanoid moves the character in the game
    out = {"Torso": A_MID.T @ torso @ A_MID, "Head": A_MID.T @ (torso.T @ conv(R[ix["head"]])) @ A_MID}
    for s, n in (("L", "Left"), ("R", "Right")):
        out[n + " Arm"] = A_SIDE[s].T @ (torso.T @ conv(R[ix["upper_arm." + s]]) @ ARM_REST[s]) @ A_SIDE[s]
        out[n + " Leg"] = A_SIDE[s].T @ (torso.T @ conv(R[ix["thigh." + s]])) @ A_SIDE[s]
    return out, A_MID.T @ off


def write_rbxmx(path, bones, clip, name, step=2, loop=True):
    frames = list(range(0, clip["frames"], step)) + [clip["frames"]]
    I = np.eye(3)
    ks = ""
    for f in frames:
        p, t = r6_poses(bones, clip, f)
        kids = "".join(_pose(k, p[k]) for k in ("Head", "Left Arm", "Right Arm", "Left Leg", "Right Leg"))
        ks += (f'<Item class="Keyframe"><Properties><string name="Name">Keyframe</string><float name="Time">{f / clip["fps"]:.4f}</float></Properties>'
               + _pose("HumanoidRootPart", I, kids=_pose("Torso", p["Torso"], t, kids), weight=0) + "</Item>")
    Path(path).write_text('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" version="4"><External>null</External><External>nil</External>'
                          f'<Item class="KeyframeSequence"><Properties><string name="Name">{sx.escape(name)}</string><bool name="Loop">{str(loop).lower()}</bool>'
                          f'<token name="Priority">2</token></Properties>{ks}</Item></roblox>', "utf-8")


# ------------------------------------------------------------------ packs
STEPS = {
    "clothes": "Одежда (classic): shirt.png, pants.png. Creator Dashboard > Avatar Items > Classics > загрузить, тип Shirt или Pants. Бесплатный тест: в Studio объект Shirt/Pants на персонаже. Публикация стоит 80 Robux. https://create.roblox.com/docs/avatar/classic-clothing",
    "anim": "Анимация: Studio > вкладка Model > Insert from File > anim_*.rbxmx. Создайте R6-персонажа (Avatar > Rig Builder), откройте Animation Editor, ... > Import > From Roblox/выберите KeyframeSequence, затем Publish. https://create.roblox.com/docs/animation/editor",
    "model": "Модель: Studio > File > Import 3D > model.glb. https://create.roblox.com/docs/art/modeling/3d-importer",
    "acc": "Аксессуары: accessories/*.glb > Import 3D, затем Accessory Fitting Tool. https://create.roblox.com/docs/art/accessories",
    "image": "Картинка: Asset Manager > Bulk Import или Creator Dashboard > Decals. Спрайт-лист: ImageLabel с ImageRectOffset и ImageRectSize. https://create.roblox.com/docs/projects/assets",
}


def _readme(out, keys, notes=()):
    (out / "README.txt").write_text("Как загрузить в Roblox\n\n" + "\n\n".join(STEPS[k] for k in keys) + ("\n\nВнимание:\n" + "\n".join(notes) if notes else "") + "\n", "utf-8")


TURN = trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0])  # our figures face +Z, Roblox avatars face -Z


def _turn_glb(path):
    """Turn a (skinned) GLB half round about Y by putting its scene under one rotated root node."""
    import json
    import struct
    b = Path(path).read_bytes()
    n = struct.unpack_from("<I", b, 12)[0]
    js, rest = json.loads(b[20:20 + n]), b[20 + n:]
    sc = js["scenes"][js.get("scene", 0)]
    js["nodes"].append({"name": "RobloxFront", "rotation": [0, 1, 0, 0], "children": sc["nodes"]})
    sc["nodes"] = [len(js["nodes"]) - 1]
    j = json.dumps(js, separators=(",", ":")).encode()
    j += b" " * (-len(j) % 4)
    Path(path).write_bytes(b[:8] + struct.pack("<I", 20 + len(j) + len(rest)) + struct.pack("<I4s", len(j), b"JSON") + j + rest)


def export_char(name):
    c = chars.load(name)
    r = rig.load(chars._rn(name))
    out = OUT / _safe(name)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    res = chars.export_c(c)
    shutil.copy(PROJECTS / res["path"], out / "model.glb")
    _turn_glb(out / "model.glb")
    H = float(np.max([b["tail"][1] for b in r["bones"]]))
    files, keys, notes = ["model.glb"], ["model"], []
    if res["max_part"] > MESH_TRIS:
        notes.append(f"В самой большой части {res["max_part"]} треугольников, в одном меше Roblox допускает {MESH_TRIS}. Поставьте качество «Среднее» или «Лоу-поли».")
    if c["template"] == "humanoid":
        for k, a in classic(c["outfit"], c["template"], H).items():
            Image.fromarray(a).save(out / f"{k}.png")
            files.append(f"{k}.png")
            keys.insert(0, "clothes") if "clothes" not in keys else None
        for n, clip in r["clips"].items():
            write_rbxmx(out / f"anim_{_safe(n)}.rbxmx", r["bones"], clip, n)
            files.append(f"anim_{_safe(n)}.rbxmx")
        if r["clips"]:
            keys.append("anim")
    acc = [g for g in c["outfit"] if g["kind"] in ACCESSORY]
    if acc:
        V, F, N, _ = rig.load_mesh(r["src"])
        fit = chars.fit_for(c, r, V, F, N)
        stamp = [r["src"], (PROJECTS / r["src"]).stat().st_mtime, 6]
        (out / "accessories").mkdir()
        for g in acc:
            if cloth.kinds_for(c["template"])[g["kind"]][2].get("pet"):
                ms, _ = chars.prop_mesh(c, r, V, F, N, g)
                if len(ms) == 1 and ms[0][1] is None:  # textured file: keep its texture
                    ms[0][0].apply_transform(TURN).export(out / "accessories" / f"{g['kind']}.glb")
                    files.append(f"accessories/{g['kind']}.glb")
                    continue
                for m, col in ms:
                    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.r_[col * 255, 255].astype(np.uint8))
                trimesh.util.concatenate([m for m, _ in ms]).apply_transform(TURN).export(out / "accessories" / f"{g['kind']}.glb")
                files.append(f"accessories/{g['kind']}.glb")
                continue
            v, f, *_ = chars._garment(c, g, fit, stamp)
            v, f = decimate(np.asarray(v, float), np.asarray(f), ACC_TRIS)
            m = trimesh.Trimesh(v, f, process=False).apply_transform(TURN)
            col = body.rgb(g.get("color") or cloth.kinds_for(c["template"])[g["kind"]][2]["color"])
            m.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=[*col, 1], roughnessFactor=.8))
            m.export(out / "accessories" / f"{g['kind']}.glb")
            files.append(f"accessories/{g['kind']}.glb")
        keys.append("acc")
    left = [g["kind"] for g in c["outfit"] if g["kind"] not in CLASSIC and g["kind"] not in ACCESSORY]
    if left:
        notes.append("Без версии для Roblox: " + ", ".join(left))
    _readme(out, keys, notes)
    return {"dir": out.relative_to(PROJECTS).as_posix(), "abs": str(out), "files": files + ["README.txt"], "notes": notes}


def export_file(path: str):
    """Any model or picture under projects/ -> a Roblox-ready copy."""
    p = PROJECTS / path
    if not p.exists():
        raise FileNotFoundError(f"нет файла {path}")
    out = OUT / _safe(p.stem)
    out.mkdir(parents=True, exist_ok=True)
    notes = []
    if p.suffix.lower() == ".glb":
        sc = trimesh.load(p, force="scene")
        big = max((len(g.faces) for g in sc.geometry.values() if hasattr(g, "faces")), default=0)
        if big > MESH_TRIS and not skins._is_rigged(p):
            for k, g in list(sc.geometry.items()):
                if len(g.faces) > MESH_TRIS:
                    v, f = decimate(g.vertices, g.faces, MESH_TRIS)
                    sc.geometry[k] = trimesh.Trimesh(v, f, process=False)
            notes.append(f"Части больше {MESH_TRIS} треугольников упрощены, цвет этих частей мог потеряться.")
            sc.export(out / "model.glb")
        else:
            shutil.copy(p, out / "model.glb")
            if big > MESH_TRIS:
                notes.append(f"В одном меше {big} треугольников, лимит {MESH_TRIS}.")
        name, key = "model.glb", "model"
    else:
        im = Image.open(p).convert("RGBA")
        if max(im.size) > IMG_MAX:
            im.thumbnail((IMG_MAX, IMG_MAX))
            notes.append(f"Картинка уменьшена до {im.size[0]}x{im.size[1]}: Roblox показывает до {IMG_MAX} px.")
        name, key = "image.png", "image"
        im.save(out / name)
    _readme(out, [key], notes)
    return {"dir": out.relative_to(PROJECTS).as_posix(), "abs": str(out), "files": [name, "README.txt"], "notes": notes}
