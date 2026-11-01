"""PBR texture packs from ambientCG (CC0, free for any use). Each library material maps to a search query;
the most popular match is downloaded (1K/2K JPG) and its maps are stored as
textures/library/<material>_<albedo|normal|roughness|ao|height|metal>.jpg"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import httpx

from .materials import TEX_LIB

API = "https://ambientcg.com/api/v2/full_json"
KINDS = {"_Color.": "albedo", "_NormalGL.": "normal", "_Roughness.": "roughness", "_AmbientOcclusion.": "ao",
         "_Displacement.": "height", "_Metalness.": "metal"}

# material -> ambientCG search query (or exact asset id via "id:Bricks076C")
QUERIES = {
    "stone_ashlar": "stone", "stone_rubble": "rock wall", "stone_dark": "rock",
    "granite": "granite", "marble": "marble", "sandstone": "sandstone", "limestone_trim": "plaster smooth beige",
    "rustication": "paving stones", "brick_red": "red bricks", "brick_yellow": "bricks", "brick_silicate": "white bricks",
    "brick_gothic": "bricks", "adobe": "facade", "plaster_white": "plaster white", "plaster_ochre": "plaster yellow",
    "plaster_pink": "plaster", "plaster_blue": "facade", "plaster_green": "plaster", "plaster_grey": "plaster",
    "concrete_panel": "concrete", "concrete_raw": "concrete", "concrete_tile": "tiles", "interior": "plaster",
    "log_pine": "logs", "log_dark": "logs", "timber_dark": "wood dark", "wood_boards": "wood planks", "wood_boards_green": "wood siding",
    "wood_painted_white": "wood siding", "wood_carved": "wood", "wood_door": "wood", "wood_floor": "wood floor",
    "shingles_wood": "wood shingles", "thatch": "thatch", "clay_tile": "roofing tiles", "clay_tile_dark": "roofing tiles",
    "slate": "roofing slate", "lead_roof": "sheet metal", "metal_roof_green": "corrugated steel", "metal_roof_red": "corrugated steel",
    "zinc": "sheet metal", "bitumen": "asphalt", "turf": "grass", "copper_green": "copper", "gold": "metal",
    "glazed_tile_green": "roofing tiles", "iron": "metal", "steel": "metal", "aluminium": "metal",
    "earth": "ground", "gravel": "gravel", "ceramic_blue": "tiles", "terracotta": "tiles", "red_paint": "metal",
    "stone_maya": "rock", "tufa": "rock", "red_sandstone": "sandstone", "glazed_tile_yellow": "roofing tiles",
    "wood_dark": "wood", "bronze": "metal", "wood_tar": "wood", "clapboard": "wood siding",
    "corrugated_metal": "corrugated steel", "frame_white": "wood", "frame_brown": "wood",
}


def _search(query: str, client: httpx.Client) -> dict | None:
    params = {"type": "Material", "limit": 5, "include": "downloadData", "sort": "Popular"}
    if query.startswith("id:"):
        params["id"] = query[3:]
    else:
        params["q"] = query
    r = client.get(API, params=params, timeout=30)
    r.raise_for_status()
    found = r.json().get("foundAssets", [])
    return found[0] if found else None


def _zip_link(asset: dict, res: str) -> tuple[str, int] | None:
    for folder in asset.get("downloadFolders", {}).values():
        for d in folder.get("downloadFiletypeCategories", {}).get("zip", {}).get("downloads", []):
            if d.get("attribute") == f"{res}-JPG":
                return d["downloadLink"], d.get("size", 0)
    return None


def have(slot: str) -> bool:
    return any((TEX_LIB / f"{slot}_albedo.{e}").exists() for e in ("jpg", "png"))


def download(slots: list[str], res: str = "1K", force=False, progress=None) -> dict:
    """Download PBR maps for material slots. Returns {slot: asset_id | 'skip' | 'error: ...'}."""
    TEX_LIB.mkdir(parents=True, exist_ok=True)
    out = {}
    src_file = TEX_LIB / "SOURCES.json"
    sources = json.loads(src_file.read_text("utf-8")) if src_file.exists() else {}
    with httpx.Client(follow_redirects=True, headers={"User-Agent": "3dPazl/0.3 texture downloader"}) as client:
        for i, slot in enumerate(slots):
            base = slot.partition("#")[0]
            if base not in QUERIES:
                out[base] = "skip: no query"
                continue
            if have(base) and not force:
                out[base] = "skip: already there"
                continue
            try:
                asset = _search(QUERIES[base], client)
                link = asset and _zip_link(asset, res)
                if not link:
                    out[base] = "error: not found"
                    continue
                url, size = link
                if progress:
                    progress(i, len(slots), base, asset["assetId"], size)
                data = client.get(url, timeout=300).content
                with zipfile.ZipFile(io.BytesIO(data)) as z:  # only image maps are extracted, nothing executed
                    for name in z.namelist():
                        low = name.lower()
                        if not low.endswith((".jpg", ".jpeg", ".png")) or "/" in name or ".." in name:
                            continue
                        for key, kind in KINDS.items():
                            if key.lower() in low:
                                ext = low.rsplit(".", 1)[1]
                                (TEX_LIB / f"{base}_{kind}.{ext}").write_bytes(z.read(name))
                sources[base] = {"asset": asset["assetId"], "url": f"https://ambientcg.com/view?id={asset['assetId']}",
                                 "license": "CC0 1.0 (ambientCG.com)", "resolution": res}
                out[base] = asset["assetId"]
            except Exception as ex:
                out[base] = f"error: {type(ex).__name__}: {ex}"
    src_file.write_text(json.dumps(sources, ensure_ascii=False, indent=1), "utf-8")
    return out
