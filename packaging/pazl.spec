# PyInstaller spec: one-folder build of the 3dPazl desktop app -> dist/3dPazl/3dPazl.exe
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent
datas = [
    (str(ROOT / "web"), "web"),
    (str(ROOT / "docs"), "docs"),
    (str(ROOT / "pazl" / "styles"), "pazl/styles"),
    (str(ROOT / "pazl" / "core" / "materials.yaml"), "pazl/core"),
    (str(ROOT / "textures" / "library"), "textures/library"),
]
binaries, hiddenimports = [], collect_submodules("pazl") + collect_submodules("uvicorn")
for pkg in ("webview", "manifold3d", "trimesh", "pyrender", "pyglet", "OpenGL", "fast_simplification", "mapbox_earcut",
            "shapely", "clr_loader", "pythonnet", "anthropic"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

a = Analysis([str(ROOT / "packaging" / "launcher.py")], pathex=[str(ROOT)], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports, excludes=["pytest", "tkinter", "matplotlib", "IPython"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="3dPazl", console=False,
          icon=str(ROOT / "packaging" / "pazl.ico"), upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="3dPazl", upx=False)
