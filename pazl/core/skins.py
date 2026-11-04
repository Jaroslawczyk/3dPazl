"""Skins: tileable procedural (or user image) materials that go on any object. A skin is a small dict
{pattern, colors, tile (metres per repeat), seed, metal, rough}; tile_image() renders it, box_uv() maps any mesh without
needing its own UVs, apply_glb() re-skins a static GLB (items, buildings, imports). Characters use it through core/chars."""
from __future__ import annotations

import json
import re
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from ..paths import PROJECTS

SKINS = PROJECTS / "skins"
N = 512
PATTERNS = {"solid": "Однотонный", "stripes": "Полосы", "checker": "Шахматка", "dots": "Горох", "spots": "Пятна", "camo": "Камуфляж",
            "plaid": "Клетка", "weave": "Ткань", "knit": "Вязка", "scales": "Чешуя", "fur": "Шерсть", "leather": "Кожа",
            "wood": "Дерево", "marble": "Мрамор", "rust": "Ржавчина", "galaxy": "Космос", "image": "Своя картинка"}
PRESETS = {
    "denim": {"title": "Джинса", "pattern": "weave", "colors": ["#2f4d7a", "#5d7ba8"], "tile": .06, "rough": .9},
    "linen": {"title": "Лён", "pattern": "weave", "colors": ["#d9d0bb", "#efe8d8"], "tile": .05, "rough": .95},
    "knit_red": {"title": "Красная вязка", "pattern": "knit", "colors": ["#9c2b2b", "#c24a44"], "tile": .06, "rough": .95},
    "tartan": {"title": "Шотландка", "pattern": "plaid", "colors": ["#7a1f24", "#1d3b2a", "#e0c35a"], "tile": .22, "rough": .85},
    "camo": {"title": "Камуфляж", "pattern": "camo", "colors": ["#4b5a32", "#2f3524", "#857a55", "#1e1f18"], "tile": .6, "rough": .8},
    "sailor": {"title": "Тельняшка", "pattern": "stripes", "colors": ["#f4f4f2", "#1f3f7a"], "tile": .05, "rough": .85},
    "leather": {"title": "Кожа", "pattern": "leather", "colors": ["#4a2c1a", "#6a4128"], "tile": .2, "rough": .55},
    "dragon": {"title": "Драконья чешуя", "pattern": "scales", "colors": ["#1f6b4f", "#7bd18f"], "tile": .14, "rough": .4, "metal": .2},
    "tiger": {"title": "Тигр", "pattern": "stripes", "colors": ["#d98a2b", "#1a1410"], "tile": .24, "wavy": 1, "rough": .8},
    "dalmatian": {"title": "Далматин", "pattern": "spots", "colors": ["#efece4", "#17171a"], "tile": .3, "rough": .8},
    "fur": {"title": "Рыжая шерсть", "pattern": "fur", "colors": ["#7a4a22", "#c58d4e"], "tile": .15, "rough": .95},
    "oak": {"title": "Дуб", "pattern": "wood", "colors": ["#6b4423", "#a67c4e"], "tile": .5, "rough": .7},
    "marble": {"title": "Мрамор", "pattern": "marble", "colors": ["#e8e6e1", "#57585e"], "tile": .7, "rough": .2},
    "rust": {"title": "Ржавый металл", "pattern": "rust", "colors": ["#6e6f73", "#7a3d1c", "#2b1a12"], "tile": .5, "rough": .75, "metal": .55},
    "chess": {"title": "Шахматка", "pattern": "checker", "colors": ["#f0f0ee", "#202024"], "tile": .2, "rough": .5},
    "polka": {"title": "Горошек", "pattern": "dots", "colors": ["#c23a4a", "#f6efe6"], "tile": .08, "rough": .7},
    "galaxy": {"title": "Космос (галактика)", "pattern": "galaxy", "colors": ["#0d0a2e", "#4b2a8f", "#c2457e", "#3f86c9"], "tile": .45, "rough": .8},
}


def rgb(c):
    c = str(c).lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], float) / 255


def noise(seed, freq, aniso=(1, 1)):
    """Tileable smooth noise in 0..1 (filtered in the frequency domain, so it wraps by construction)."""
    w = np.random.default_rng(seed).standard_normal((N, N))
    fy, fx = np.fft.fftfreq(N)[:, None] * N * aniso[0], np.fft.fftfreq(N)[None, :] * N * aniso[1]
    a = np.real(np.fft.ifft2(np.fft.fft2(w) * np.exp(-(fx ** 2 + fy ** 2) / (2 * freq ** 2))))
    r = a.argsort(axis=None).argsort().reshape(N, N) / (N * N - 1)  # uniform histogram: thresholds mean area shares
    return r


def _mix(c, t):
    return c[0] * (1 - t[..., None]) + c[1] * t[..., None]


def _levels(c, v):
    i = np.minimum((v * len(c)).astype(int), len(c) - 1)
    return np.array(c)[i]


def tile_array(s):
    pat = s.get("pattern", "solid")
    c = [rgb(x) for x in (s.get("colors") or ["#b0b0b0", "#505050"])]
    c = c if len(c) > 1 else c + [c[0] * .7]
    seed = int(s.get("seed", 1))
    y, x = np.mgrid[0:N, 0:N] / N
    T = 2 * np.pi
    if pat == "solid":
        return np.broadcast_to(c[0], (N, N, 3)).copy()
    if pat == "stripes":
        v = y + (noise(seed, 3) - .5) * .35 * float(s.get("wavy", 0))
        return _mix(c, np.clip(np.sin(T * 2 * v) * 6 + .5, 0, 1))
    if pat == "checker":
        return _mix(c, ((x * 2).astype(int) + (y * 2).astype(int)) % 2 * 1.0)
    if pat == "dots":
        d = np.hypot((x * 4 % 1) - .5, (y * 4 % 1) - .5)
        return _mix(c, np.clip((.28 - d) * 40, 0, 1))
    if pat == "spots":
        return _mix(c, np.clip((noise(seed, 7) - .78) * 30, 0, 1))
    if pat == "camo":
        v = noise(seed, 5) * .8 + noise(seed + 1, 16) * .2
        return _levels(c, v.argsort(axis=None).argsort().reshape(N, N) / (N * N))
    if pat == "plaid":
        a = (np.sin(T * 3 * x) > .3) * .5 + (np.sin(T * 3 * y) > .3) * .5
        o = _mix(c, a)
        line = (np.abs((x * 3 % 1) - .1) < .012) | (np.abs((y * 3 % 1) - .1) < .012)
        o[line] = c[2] if len(c) > 2 else c[1]
        return o
    if pat == "weave":
        a = np.sin(T * 64 * x) * np.sin(T * 64 * y)
        return _mix(c, np.clip(.45 + a * .35 + (noise(seed, 40) - .5) * .5, 0, 1))
    if pat == "knit":
        v = (np.abs((x * 24 % 1) - .5) * 2 + y * 16) % 1
        return _mix(c, v) * (.8 + .2 * np.abs(np.sin(T * 12 * x)))[..., None]
    if pat == "scales":
        n, best, top = 8, np.full((N, N), 9.0), np.zeros((N, N))
        for row in range(-1, n * 2 + 2):  # later rows lie over earlier ones
            cy = row / (n * 2)
            for off in (0, .5):
                if row % 2 != int(off * 2):
                    continue
                dx = ((x * n - off + .5) % 1) - .5
                dy = ((y - cy + .5) % 1 - .5) * n
                d = np.hypot(dx, dy * 1.0)
                m = (d < .62) & (dy <= .1)
                best[m], top[m] = d[m], 1
        return _mix(c, np.clip(best / .62, 0, 1)) * (.55 + .45 * (best < .56))[..., None]
    if pat == "fur":
        return _mix(c, noise(seed, 60, (.12, 1)) * .7 + noise(seed + 2, 6) * .3)
    if pat == "leather":
        a = np.abs(noise(seed, 22) - .5) * 2
        return _mix(c, noise(seed + 1, 6)) * (.72 + .28 * np.clip(a * 3, 0, 1))[..., None]
    if pat == "wood":
        v = np.sin(T * (4 * x + noise(seed, 3, (.15, 1)) * 3)) * .5 + .5
        return _mix(c, v * .75 + noise(seed + 1, 70, (.04, 1)) * .25)
    if pat == "marble":
        v = np.abs(np.sin(T * (x + y + noise(seed, 4) * 1.6)))
        return _mix(c, np.clip(1 - v, 0, 1) ** 3 * 1.3 + 0 * x)
    if pat == "rust":
        a = noise(seed, 6) * .75 + noise(seed + 1, 40) * .25
        o = _mix(c, np.clip((a - .5) * 8, 0, 1))
        return np.where((np.clip(noise(seed + 2, 30), 0, 1) > .9)[..., None], c[2] if len(c) > 2 else c[1], o)
    if pat == "galaxy":  # dark sky, two-colour nebula, a cyan glow and stars (single pixels and a few crosses)
        base, neb = c[0], _mix([c[1], c[2] if len(c) > 2 else c[1]], noise(seed + 1, 6))
        a = np.clip((noise(seed, 3) - .3) * 1.8, 0, 1) ** 1.4
        o = base * (1 - a[..., None]) + neb * a[..., None]
        g = np.clip((noise(seed + 2, 9) - .8) * 3, 0, 1)[..., None] * .6
        o = o * (1 - g) + (c[3] if len(c) > 3 else c[1]) * g
        r = np.random.default_rng(seed).random((N, N))
        big = r > .9993
        star = (r > .996) | big | np.roll(big, 1, 0) | np.roll(big, -1, 0) | np.roll(big, 1, 1) | np.roll(big, -1, 1)
        o[star] = 1
        return o
    raise ValueError(f"unknown pattern {pat}; have {list(PATTERNS)}")


def resolve(s):
    """Skin by preset/saved name or inline dict."""
    if isinstance(s, str):
        if s in PRESETS:
            return PRESETS[s]
        p = SKINS / f"{_safe(s)}.skin.json"
        if p.exists():
            return json.loads(p.read_text("utf-8"))
        raise KeyError(f"unknown skin {s}; presets: {', '.join(PRESETS)}")
    return s


def tile_image(s) -> Image.Image:
    s = resolve(s)
    if s.get("pattern") == "image":
        return Image.open(PROJECTS / s["file"]).convert("RGB")
    return Image.fromarray((np.clip(tile_array(s), 0, 1) * 255).astype(np.uint8))


def png_bytes(s) -> bytes:
    b = BytesIO()
    tile_image(s).save(b, "PNG")
    return b.getvalue()


def box_uv(V, F, tile):
    """Cube projection for any mesh: each face takes UVs from its dominant axis. Returns (src vertex index per new vertex,
    new faces, uv); pattern scale is real-world, so a skin looks the same size on a mug and on a tower."""
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    ax = np.abs(n).argmax(1)
    key = F * 3 + ax[:, None]
    uniq, inv = np.unique(key.ravel(), return_inverse=True)
    idx, a = uniq // 3, uniq % 3
    P = V[idx]
    u = np.where(a == 0, P[:, 2], P[:, 0])
    v = np.where(a == 1, P[:, 2], P[:, 1])
    return idx, inv.reshape(-1, 3), np.stack([u, v], 1) / float(tile)


# ------------------------------------------------------------------ textures from the internet (CC0 only)
UA = {"User-Agent": "3dPazl texture browser"}
RU = {"джинс": "denim", "ткан": "fabric", "кож": "leather", "дерев": "wood", "камен": "rock", "металл": "metal", "кирпич": "brick",
      "мех": "fur", "шерст": "wool", "трав": "grass", "песок": "sand", "плитк": "tiles", "ржав": "rust", "вязан": "knit", "ковёр": "carpet"}


def _en(q):
    q = q.strip().lower()
    return next((v for k, v in RU.items() if k in q), q)


def web_search(q, limit=24):
    """[{source, id, title, thumb, license}] from Poly Haven and ambientCG; a dead source is simply skipped."""
    import httpx
    q, out = _en(q), []
    with httpx.Client(follow_redirects=True, headers=UA, timeout=20) as c:
        try:
            a = c.get("https://api.polyhaven.com/assets", params={"t": "textures"}).json()
            for k, v in a.items():
                if q in " ".join([k, v["name"], *v.get("tags", []), *v.get("categories", [])]).lower():
                    out.append({"source": "polyhaven", "id": k, "title": v["name"], "license": "CC0",
                                "thumb": f"https://cdn.polyhaven.com/asset_img/thumbs/{k}.png?width=128&height=128", "downloads": v.get("download_count", 0)})
            out.sort(key=lambda x: -x.pop("downloads"))
        except (httpx.HTTPError, ValueError):
            pass
        try:
            a = c.get("https://ambientcg.com/api/v2/full_json", params={"q": q, "type": "Material", "limit": limit, "include": "imageData"}).json()
            for v in a.get("foundAssets", []):
                im = v.get("previewImage") or {}
                out.append({"source": "ambientcg", "id": v["assetId"], "title": v.get("displayName") or v["assetId"], "license": "CC0",
                            "thumb": im.get("128-PNG") or im.get("256-PNG") or ""})
        except (httpx.HTTPError, ValueError):
            pass
    return out[:limit]


def web_download(source, asset, res="1k"):
    """Save a web texture as a skin; returns its name. Colour map only, 1k: enough for clothes, small in the GLB."""
    import io
    import zipfile
    import httpx
    SKINS.mkdir(parents=True, exist_ok=True)
    name = _safe(f"web_{asset}").lower()
    with httpx.Client(follow_redirects=True, headers=UA, timeout=120) as c:
        if source == "polyhaven":
            info = c.get(f"https://api.polyhaven.com/info/{asset}").json()
            files = c.get(f"https://api.polyhaven.com/files/{asset}").json()
            m = files.get("Diffuse") or files.get("diffuse") or files.get("albedo") or files["Color"]
            data = c.get(m[res]["jpg"]["url"]).raise_for_status().content
            dim = info.get("dimensions") or [1000]
            tile, url = float(dim[0]) / 1000, f"https://polyhaven.com/a/{asset}"
        elif source == "ambientcg":
            z = c.get(f"https://ambientcg.com/get?file={asset}_{res.upper()}-JPG.zip").raise_for_status().content
            with zipfile.ZipFile(io.BytesIO(z)) as f:
                data = f.read(next(n for n in f.namelist() if "_Color." in n))
            tile, url = 1.0, f"https://ambientcg.com/view?id={asset}"
        else:
            raise KeyError(f"unknown source {source}")
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.save(SKINS / f"{name}.jpg", quality=90)
    save(name, {"title": asset, "pattern": "image", "file": f"skins/{name}.jpg", "tile": tile, "rough": .8, "source": url, "license": "CC0"})
    return {"name": name, "tile_m": tile, "source": url, "license": "CC0"}


def _safe(n):
    return re.sub(r"[^\w\-]+", "_", n or "skin").strip("_") or "skin"


def catalog():
    saved = sorted(p.name[:-10] for p in SKINS.glob("*.skin.json")) if SKINS.exists() else []
    return {"patterns": PATTERNS, "presets": {k: v["title"] for k, v in PRESETS.items()}, "saved": saved}


def save(name, s):
    SKINS.mkdir(parents=True, exist_ok=True)
    (SKINS / f"{_safe(name)}.skin.json").write_text(json.dumps(s, ensure_ascii=False), "utf-8")
    return _safe(name)


def preview(s, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tile_image(s).save(path)


def _is_rigged(path):
    b = Path(path).read_bytes()[:4 * 1024 * 1024]
    return b[:4] == b"glTF" and b'"skins"' in b[20:20 + int.from_bytes(b[12:16], "little")]


def parts_of(src: str):
    import trimesh
    return sorted(trimesh.load(PROJECTS / src, force="scene").geometry)


def apply_glb(src: str, s, out_name="", parts=None) -> dict:
    """Skin a static GLB under projects/ into projects/skins/<out_name>.glb. parts: geometry names to skin (default all)."""
    import trimesh
    s = resolve(s)
    path = PROJECTS / src
    if _is_rigged(path):
        raise ValueError("это GLB со скелетом: скин персонажа ставится в мастерской «Персонажи»")
    sc = trimesh.load(path, force="scene")
    scale = {}
    for node in sc.graph.nodes_geometry:
        T, g = sc.graph[node]
        scale[g] = abs(np.linalg.det(T[:3, :3])) ** (1 / 3) or 1
    img = tile_image(s)
    pbr = trimesh.visual.material.PBRMaterial(name="skin", baseColorTexture=img, metallicFactor=float(s.get("metal", 0)),
                                              roughnessFactor=float(s.get("rough", .7)))
    done = 0
    for name, m in list(sc.geometry.items()):
        if parts and name not in parts or not hasattr(m, "faces") or not len(m.faces):
            continue
        V = np.asarray(m.vertices)
        idx, F, uv = box_uv(V, np.asarray(m.faces), float(s.get("tile", .3)) / scale.get(name, 1))
        t = trimesh.Trimesh(V[idx], F, process=False)
        t.visual = trimesh.visual.TextureVisuals(uv=uv, material=pbr)
        sc.geometry[name] = t
        done += 1
    if not done:
        raise ValueError("нет подходящих частей модели")
    out = SKINS / f"{_safe(out_name or Path(src).stem + '_skin')}.glb"
    out.parent.mkdir(parents=True, exist_ok=True)
    sc.export(out)
    return {"path": out.relative_to(PROJECTS).as_posix(), "parts": done, "kb": round(out.stat().st_size / 1e3)}
