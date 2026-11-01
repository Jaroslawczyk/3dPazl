"""Material library, role resolution and texture manifest."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from ..paths import ROOT, TEX_LIB

HERE = Path(__file__).parent

# role -> fallback material when a style does not define it
ROLE_DEFAULTS = {
    "wall": "plaster_white", "plinth": "stone_rubble", "roof": "clay_tile", "trim": "limestone_trim",
    "frame": "frame_white", "glass": "glass", "door": "wood_door", "floor": "wood_floor",
    "interior": "interior", "gable": "@wall", "column": "limestone_trim", "dome": "copper_green",
    "metal": "iron", "wood": "wood_boards", "timber": "timber_dark", "stone": "stone_ashlar",
    "accent": "gold", "ground": "earth", "log": "log_pine", "seam": "sealant", "railing": "iron",
    "shutter": "wood_boards_green", "cross": "gold", "chimney": "brick_red", "stairs": "stone_ashlar",
}


class Materials:
    def __init__(self):
        self.lib: dict[str, dict] = yaml.safe_load((HERE / "materials.yaml").read_text("utf-8"))
        self.art: dict[str, dict] = {}   # dynamic per-project artwork slots

    def resolve(self, name: str, style: dict | None) -> str:
        if not name:
            name = "wall"
        if "#" in name:  # painted variant "base#rrggbb" or plain "#rrggbb"
            base, _, hexc = name.partition("#")
            return (self.resolve(base, style) if base else "default") + "#" + hexc.lower()
        seen = 0
        while seen < 5:
            seen += 1
            if name.startswith("@"):
                name = name[1:]
            if name in self.lib or name in self.art:
                return name
            smap = (style or {}).get("materials", {})
            if name in smap:
                name = smap[name]
                continue
            if name in ROLE_DEFAULTS:
                name = ROLE_DEFAULTS[name]
                continue
            break
        return name if (name in self.lib or name in self.art) else "default"

    def art_slot(self, eid: str, kind: str, subject: str, color=None) -> str:
        slot = f"art_{kind}_{hashlib.md5((eid + subject).encode()).hexdigest()[:6]}"
        base = {"mosaic": "mosaic", "stained_glass": "stained_glass"}.get(kind, "default")
        self.art[slot] = {**self.lib[base], "prompt": f"{kind.replace('_', ' ')}: {subject}. Single image, not tileable, fills the whole frame",
                          "tile": 0, "unique": True, "element": eid}
        if color:
            self.art[slot]["color"] = color
        return slot

    def get(self, name: str) -> dict:
        if "#" in name:
            base, _, hexc = name.partition("#")
            info = dict(self.get(base or "default"))
            try:
                info["color"] = [int(hexc[i:i + 2], 16) for i in (0, 2, 4)]
                info["tint"] = True
            except ValueError:
                pass
            return info
        return self.art.get(name) or self.lib.get(name) or self.lib["default"]

    def texture_files(self, name: str, tex_dir: Path) -> dict:
        """Find texture files for a slot: <dir>/<slot>_albedo.png etc. Project dir wins over library."""
        found = {}
        name = name.partition("#")[0]  # painted variants use the base material's maps (tinted)
        for kind in ("albedo", "normal", "roughness", "ao", "height", "metal"):
            for d in (tex_dir, TEX_LIB):
                for ext in ("png", "jpg", "jpeg", "webp"):
                    f = d / f"{name}_{kind}.{ext}"
                    if f.exists():
                        found[kind] = f
                        break
                if kind in found:
                    break
        return found

    def manifest(self, used: list[str], tex_dir: Path) -> dict:
        items = []
        for name in sorted(set(used)):
            m = self.get(name)
            unique = m.get("unique", False)
            items.append({
                "slot": name,
                "files": {k: f"{name}_{k}.png" for k in ("albedo", "normal", "roughness")},
                "folder": str(tex_dir if unique else TEX_LIB),
                "size_px": 1024,
                "tile_m": m.get("tile", 2),
                "tileable": not unique,
                "prompt": (m["prompt"] + (", seamless tileable PBR texture, orthographic, even lighting, no shadows"
                                          if not unique else ", front orthographic view, even lighting")),
                "have": sorted(self.texture_files(name, tex_dir).keys()),
            })
        return {"how_to": "Generate PNGs named exactly as in 'files' and put them into 'folder' "
                          "(albedo required, normal/roughness optional), then press 'Apply textures' "
                          "or call apply_textures. Library textures are shared between all projects.",
                "materials": items}


MATS = Materials()


def write_manifest(used, tex_dir: Path) -> Path:
    tex_dir.mkdir(parents=True, exist_ok=True)
    data = MATS.manifest(used, tex_dir)
    p = tex_dir / "manifest.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    md = ["# Texture prompts\n"] + [f"- **{i['slot']}** → `{i['folder']}\\{i['files']['albedo']}` "
                                    f"({i['size_px']}px, tile {i['tile_m']} m): {i['prompt']}" for i in data["materials"]]
    (tex_dir / "PROMPTS.md").write_text("\n".join(md), "utf-8")
    return p
