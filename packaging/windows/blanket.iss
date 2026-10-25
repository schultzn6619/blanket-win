; Copyright 2026 Rafael Mardojai CM
; SPDX-License-Identifier: GPL-3.0-or-later
;
; Inno Setup script of the Windows installer, built after the PyInstaller
; bundle (dist\Blanket) from the repository root:
;
;     iscc /DAppVersion=0.8.0 packaging\windows\blanket.iss
;
; Installs per user by default (no administrator rights needed), the
; installer offers an all-users install too.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

#define AppName "Blanket"
#define AppExe "Blanket.exe"
#define AppUserModelID "com.rafaelmardojai.Blanket"
#define RepoURL "https://github.com/schultzn6619/blanket-win"

[Setup]
AppId={{60793E11-FDEF-475A-ADE4-BDE796299D51}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Blanket contributors
AppPublisherURL={#RepoURL}
AppSupportURL={#RepoURL}/issues
AppUpdatesURL={#RepoURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
LicenseFile=..\..\COPYING
SetupIconFile=..\..\data\blanket.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir=..\..\dist
OutputBaseFilename=Blanket-{#AppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Blanket saves its state and quits when asked through the Restart Manager
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Files of a previous version that this one no longer ships
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\..\dist\Blanket\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon

[Registry]
; Autostart is set up from Blanket's preferences; only remove it on uninstall
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "Blanket"; Flags: uninsdeletevalue dontcreatekey

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
