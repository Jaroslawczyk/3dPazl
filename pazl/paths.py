"""App paths. From source everything lives in the repo; in the installed exe (PyInstaller) read-only resources
come from the bundle and writable data (projects, texture library) from %LOCALAPPDATA%\3dPazl."""
import os
import shutil
import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
ROOT = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "3dPazl" if FROZEN else ROOT
PROJECTS = DATA / "projects"
TEX_LIB = DATA / "textures" / "library"

if FROZEN and not TEX_LIB.exists():
    shutil.copytree(ROOT / "textures" / "library", TEX_LIB)
PROJECTS.mkdir(parents=True, exist_ok=True)
