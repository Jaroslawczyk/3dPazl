; Inno Setup script: wraps dist/3dPazl into a normal Windows installer -> dist/3dPazl-Setup-<ver>.exe
#define AppVer "0.7.1"

[Setup]
AppId={{5A678BF8-6D47-4817-B0B8-3C20944C5A2A}
AppName=3dPazl
AppVersion={#AppVer}
AppPublisher=Yaraslau
DefaultDirName={autopf}\3dPazl
DefaultGroupName=3dPazl
UninstallDisplayIcon={app}\3dPazl.exe
SetupIconFile=pazl.ico
OutputDir=..\dist
OutputBaseFilename=3dPazl-Setup-{#AppVer}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\3dPazl\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\3dPazl"; Filename: "{app}\3dPazl.exe"
Name: "{group}\{cm:UninstallProgram,3dPazl}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\3dPazl"; Filename: "{app}\3dPazl.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\3dPazl.exe"; Description: "{cm:LaunchProgram,3dPazl}"; Flags: nowait postinstall skipifsilent
