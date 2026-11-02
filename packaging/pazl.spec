# PyInstaller spec: one-folder build of the 3dPazl desktop app -> dist/3dPazl/3dPazl.exe
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).parent
ns = {}
exec((ROOT / "pazl" / "__init__.py").read_text("utf-8"), ns)
VER = tuple(int(x) for x in ns["__version__"].split(".")) + (0,)
from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,  # noqa: E402
                                                 VarFileInfo, VarStruct, VSVersionInfo)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=VER, prodvers=VER),
    kids=[StringFileInfo([StringTable("040904B0", [
        StringStruct("CompanyName", ns["__author__"]),
        StringStruct("FileDescription", "3dPazl - building constructor"),
        StringStruct("FileVersion", ns["__version__"]),
        StringStruct("InternalName", "3dPazl"),
        StringStruct("LegalCopyright", ns["__copyright__"] + ". Non-commercial license; commercial use only under a written "
                     "agreement: " + ns["__email__"]),
        StringStruct("OriginalFilename", "3dPazl.exe"),
        StringStruct("ProductName", "3dPazl"),
        StringStruct("ProductVersion", ns["__version__"]),
        StringStruct("Comments", "Author: " + ns["__author__"] + " <" + ns["__email__"] + ">")])]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])])])
datas = [
    (str(ROOT / "web"), "web"),
    (str(ROOT / "docs"), "docs"),
    (str(ROOT / "pazl" / "styles"), "pazl/styles"),
    (str(ROOT / "pazl" / "core" / "materials.yaml"), "pazl/core"),
    (str(ROOT / "textures" / "library"), "textures/library"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.txt"), "."),
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
          icon=str(ROOT / "packaging" / "pazl.ico"), upx=False, version=version_info)
coll = COLLECT(exe, a.binaries, a.datas, name="3dPazl", upx=False)
