@echo off
rem Builds dist\3dPazl\3dPazl.exe (PyInstaller) and dist\3dPazl-Setup-<ver>.exe (Inno Setup 6).
cd /d "%~dp0.."
.venv\Scripts\pip install -q pyinstaller || exit /b 1
.venv\Scripts\python packaging\make_icon.py || exit /b 1
.venv\Scripts\python packaging\third_party.py || exit /b 1
.venv\Scripts\python -m PyInstaller --noconfirm --distpath dist --workpath build packaging\pazl.spec || exit /b 1
set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" (echo Inno Setup 6 not found: winget install JRSoftware.InnoSetup & exit /b 1)
"%ISCC%" packaging\installer.iss
