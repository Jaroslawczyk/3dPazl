"""PyInstaller entry point: runs the desktop app (pazl/__main__.py).
A windowed exe has no console (sys.stdout/stderr are None): send them to %LOCALAPPDATA%\\3dPazl\\3dPazl.log, so
errors are visible and libraries that log to stderr (uvicorn) do not fail."""
import os
import runpy
import sys
from pathlib import Path

if sys.stdout is None or sys.stderr is None:
    log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "3dPazl"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = open(log_dir / ("3dPazl-mcp.log" if "--mcp" in sys.argv else "3dPazl.log"), "w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stdout or log
    sys.stderr = sys.stderr or log

runpy.run_module("pazl", run_name="__main__", alter_sys=True)
