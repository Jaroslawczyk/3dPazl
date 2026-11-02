"""Writes THIRD_PARTY_NOTICES.txt: every installed Python package that the build bundles, with its license text,
plus three.js and the CC0 texture packs. Run before PyInstaller (build.bat does)."""
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "THIRD_PARTY_NOTICES.txt"
SKIP = {"pip", "setuptools", "wheel", "pyinstaller", "pyinstaller-hooks-contrib", "pytest", "pluggy", "iniconfig",
        "altgraph", "pefile", "pywin32-ctypes", "packaging"}


def license_text(dist) -> str:
    texts = []
    for f in dist.files or []:
        name = f.name.lower()
        if name.startswith(("license", "licence", "copying", "notice")) and "dist-info" in str(f.parent).lower() + "/":
            try:
                texts.append(Path(dist.locate_file(f)).read_text(encoding="utf-8", errors="replace").strip())
            except (OSError, ValueError, IsADirectoryError):
                pass
    return "\n\n".join(texts)


def main():
    parts = [
        "THIRD-PARTY NOTICES / СТОРОННИЕ КОМПОНЕНТЫ\n"
        "3dPazl (c) Yaraslau Sychou is licensed under the 3dPazl Non-Commercial License (see LICENSE).\n"
        "The components below are NOT covered by that license; each stays under its own license.\n",
        "three.js (web/vendor) - MIT License\n" + (ROOT / "web" / "vendor" / "THREE_LICENSE").read_text("utf-8").strip(),
        "PBR texture packs downloaded by the program (ambientCG / Poly Haven) - CC0 1.0 (public domain).",
    ]
    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"]
        if not name or name.lower() in SKIP:
            continue
        lic = dist.metadata.get("License-Expression") or dist.metadata.get("License") or ""
        if len(lic) > 120:
            lic = lic.splitlines()[0][:120]
        classifiers = [c.split("::")[-1].strip() for c in dist.metadata.get_all("Classifier") or [] if c.startswith("License")]
        head = f"{name} {dist.version} - {lic or ', '.join(classifiers) or 'see package'}"
        url = dist.metadata.get("Home-page") or ""
        body = license_text(dist)
        parts.append(head + (f"\n{url}" if url else "") + (f"\n\n{body}" if body else ""))
    OUT.write_text(("\n\n" + "=" * 78 + "\n\n").join(parts) + "\n", "utf-8")
    print(f"{OUT.name}: {len(parts) - 3} packages")
    # Inno Setup shows Cyrillic in a .txt license page only with a UTF-8 BOM
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "LICENSE.txt").write_text((ROOT / "LICENSE").read_text("utf-8"), "utf-8-sig")


if __name__ == "__main__":
    main()
