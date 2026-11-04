"""Repair a model file in place until mesh_check is clean (or nothing more can be done), keeping UVs, skin, clips.

    .venv/Scripts/python.exe scripts/mesh_fix.py chars/hero.glb"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from pazl.core import meshfix  # noqa: E402

if __name__ == "__main__":
    r = meshfix.fix(sys.argv[1], log=print)
    print(f"{r['model']}: {r['before'] or 'clean'} -> {r['after'] or 'clean'}")
