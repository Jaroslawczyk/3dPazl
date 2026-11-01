"""PyInstaller entry point: runs the desktop app (pazl/__main__.py)."""
import runpy

runpy.run_module("pazl", run_name="__main__", alter_sys=True)
