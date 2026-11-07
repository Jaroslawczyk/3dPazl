#!/usr/bin/env python3
"""Generate seamless PBR tile textures into assets/tiles/."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import tile_gens
from scripts.tilelib import TILES_ROOT, save_set, write_manifest


def _parse_only(s: str | None) -> set[str] | None:
    if not s:
        return None
    return {p.strip().lower() for p in s.split(",") if p.strip()}


def generate(size: int, only: set[str] | None, variants: int = 3, base_seed: int = 42):
    entries: list[dict] = []
    rows = []
    if only:
        manifest_path = TILES_ROOT / "manifest.json"
        if manifest_path.exists():
            import json

            prev = json.loads(manifest_path.read_text(encoding="utf-8")).get("textures", [])
            prev = [e for e in prev if e.get("category", "").lower() not in only]
            entries.extend(prev)
    for key in sorted(tile_gens._REGISTRY):
        category, name = key.split("/", 1)
        if only and category.lower() not in only:
            continue
        fn = tile_gens.get_generator(key)
        tile_m = getattr(fn, "tile_meters", 1.0)
        for v in range(variants):
            suffix = f"_v{v + 1}" if variants > 1 else ""
            out_name = f"{name}{suffix}"
            out_dir = TILES_ROOT / category / out_name
            seed = base_seed + hash(key) % 10000 + v * 137
            data = fn(size, seed, v)
            save_set(
                out_dir,
                data["albedo"],
                data["height"],
                data["roughness"],
                data.get("metallic"),
                albedo_rgba=data.get("albedo_rgba", False),
                emissive=data.get("emissive"),
            )
            ppm = size / tile_m
            entries.append(
                {
                    "path": str(out_dir.relative_to(ROOT)).replace("\\", "/"),
                    "category": category,
                    "name": out_name,
                    "size": size,
                    "tile_meters": tile_m,
                    "px_per_m": ppm,
                    "maps": [
                        "albedo.png",
                        "height.png",
                        "normal.png",
                        "ao.png",
                        "roughness.png",
                        "metallic.png",
                        "preview.png",
                    ],
                }
            )
            rows.append((out_name, size, tile_m, category))
    write_manifest(entries, size)
    print(f"Generated {len(entries)} texture sets under {TILES_ROOT}")
    for name, sz, tm, cat in rows[:5]:
        print(f"  {cat}/{name} {sz}px tile={tm}m")
    if len(rows) > 5:
        print(f"  ... +{len(rows) - 5} more")


def list_textures():
    for cat, name, tm in tile_gens.all_specs():
        print(f"{cat}/{name}  tile_m={tm}")


def main():
    ap = argparse.ArgumentParser(description="Procedural seamless PBR tiles")
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--only", type=str, default=None, help="categories: wall,roof,ground,...")
    ap.add_argument("--variants", type=int, default=3)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--brick-only", action="store_true", help="quick test: wall_brick_red v1")
    args = ap.parse_args()
    size = args.size
    if size & (size - 1):
        print("size must be power of two", file=sys.stderr)
        sys.exit(2)

    if args.list:
        list_textures()
        return

    if args.brick_only:
        fn = tile_gens.get_generator("wall/wall_brick_red")
        out = TILES_ROOT / "wall" / "wall_brick_red_v1"
        data = fn(size, 42, 0)
        save_set(out, data["albedo"], data["height"], data["roughness"], data["metallic"])
        print("Wrote", out)
        return

    generate(size, _parse_only(args.only), variants=args.variants)


if __name__ == "__main__":
    main()
