"""Bridge to an installed Blender, used as a headless backend by the workshops (items, clothing, rig & animation):
automatic skin weights, Rigify metarigs, cloth simulation, skinned/animated GLB export, turntable renders.

Blender is never bundled or copied (it is GPL): we only run the user's own blender.exe as a separate process,
`blender -b --factory-startup --python <script> -- <json args>`. Scripts live in pazl/blender_scripts/; each
reads its arguments from JSON after `--` and prints one line `PAZL_RESULT <json>` with its result."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "blender_scripts"
_CANDIDATES = [
    r"F:\steam\steamapps\common\Blender\blender.exe",
    r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe",
    r"C:\Program Files\Steam\steamapps\common\Blender\blender.exe",
]


def _program_files() -> list[str]:
    out = []
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        root = Path(base or "") / "Blender Foundation"
        if base and root.is_dir():  # newest version first
            out += [str(p / "blender.exe") for p in sorted(root.iterdir(), reverse=True)]
    return out


@lru_cache(maxsize=1)
def find() -> str | None:
    """Path to blender.exe: $PAZL_BLENDER, Steam, Program Files, then PATH. None if Blender is not installed."""
    for c in [os.environ.get("PAZL_BLENDER", ""), *_CANDIDATES, *_program_files()]:
        if c and Path(c).is_file():
            return c
    return shutil.which("blender")


def run(script: str, args: dict | None = None, timeout: float = 600) -> dict:
    """Run pazl/blender_scripts/<script>.py headless; returns the dict it printed as `PAZL_RESULT {...}`."""
    exe = find()
    if not exe:
        raise RuntimeError("Blender not found: install it (e.g. from Steam) or set the PAZL_BLENDER environment variable")
    path = SCRIPTS / f"{script}.py"
    if not path.is_file():
        raise FileNotFoundError(path)
    cmd = [exe, "-b", "--factory-startup", "--python-exit-code", "3", "--python", str(path), "--", json.dumps(args or {})]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for line in reversed(p.stdout.splitlines()):
        if line.startswith("PAZL_RESULT "):
            return json.loads(line[len("PAZL_RESULT "):])
    tail = "\n".join((p.stdout + p.stderr).splitlines()[-15:])
    raise RuntimeError(f"Blender script {script} failed (exit {p.returncode}):\n{tail}")


@lru_cache(maxsize=1)
def info() -> dict:
    """{found, path, version, addons} - what the workshops can rely on (cached; Blender start takes a few seconds)."""
    exe = find()
    if not exe:
        return {"found": False}
    try:
        return {"found": True, "path": exe, **run("probe", timeout=120)}
    except Exception as e:  # noqa: BLE001 - report, never crash the app because of Blender
        return {"found": True, "path": exe, "error": str(e)[-400:]}
