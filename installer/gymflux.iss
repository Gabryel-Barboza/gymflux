; GymFlux Inno Setup — Fase 5.1 (Windows 10/11 64-bit, dual-exe)
; Gera GymFlux-Setup-vX.Y.Z.exe a partir de dist\GymFlux.exe (x64, UI) +
; dist\GymFlux.HardwareHelper.exe (x86, COM 32-bit oculto via IPC stdio).
; kernel7x.dll NÃO é bundlada (vendor/ ignorado); sem DLL o app cai p/ mock.

#define MyAppName "GymFlux"
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "GymFlux"
#define MyAppURL "https://github.com/anomalyco/opencode"
#define MyAppExeName "GymFlux.exe"

[Setup]
AppId={{631F33FA-6DD0-4080-89E2-2E7D10F7F8FA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\GymFlux
DefaultGroupName={#MyAppName}
OutputDir=..\dist\installer
OutputBaseFilename=GymFlux-Setup-v{#MyAppVersion}
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x86compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\LICENSE
#ifexist "..\src\gymflux\ui\assets\icon.ico"
SetupIconFile=..\src\gymflux\ui\assets\icon.ico
#endif
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no
; manter desfazer limpo
DisableDirPage=no
DisableProgramGroupPage=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Iniciar com o Windows (bandeja)"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; UI 64-bit (onefile windowed) + helper 32-bit COM (onefile console, oculto)
Source: "..\dist\GymFlux.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\GymFlux.HardwareHelper.exe"; DestDir: "{app}"; Flags: ignoreversion
; LICENSE já no Setup, opcional duplicar no app
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "ui"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "ui"; Tasks: desktopicon; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "ui"; Tasks: startupicon; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "ui"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; não apaga %APPDATA%\GymFlux (DB + config do usuário) — preserva dados na desinstalação
Type: filesandordirs; Name: "{app}"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
