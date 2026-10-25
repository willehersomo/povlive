; Instalador do PovLive para Windows (Inno Setup 6). O CI gera dist\PovLive com o PyInstaller antes.
#define Versao GetEnv("POVLIVE_VERSAO")

[Setup]
AppId={{6C1E3B52-8E7A-4C9B-9B0A-5F2D7C4E1A30}
AppName=PovLive
AppVersion={#Versao}
AppPublisher=Breno Wille
AppPublisherURL=https://github.com/willehersomo/povlive
AppSupportURL=https://github.com/willehersomo/povlive/issues
DefaultDirName={autopf}\PovLive
DefaultGroupName=PovLive
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist
OutputBaseFilename=PovLive-{#Versao}-setup
SetupIconFile=..\povlive.ico
UninstallDisplayIcon={app}\PovLive.exe
LicenseFile=..\..\LICENSE
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[CustomMessages]
en.Associar=Open .pov files with PovLive
pt.Associar=Abrir arquivos .pov com o PovLive
en.Cena=POV-Ray scene
pt.Cena=Cena do POV-Ray

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associar"; Description: "{cm:Associar}"

[Files]
Source: "..\..\dist\PovLive\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\PovLive"; Filename: "{app}\PovLive.exe"
Name: "{autodesktop}\PovLive"; Filename: "{app}\PovLive.exe"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.pov\OpenWithProgids"; ValueType: string; ValueName: "PovLive.pov"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associar
Root: HKA; Subkey: "Software\Classes\.inc\OpenWithProgids"; ValueType: string; ValueName: "PovLive.pov"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associar
Root: HKA; Subkey: "Software\Classes\PovLive.pov"; ValueType: string; ValueName: ""; ValueData: "{cm:Cena}"; Flags: uninsdeletekey; Tasks: associar
Root: HKA; Subkey: "Software\Classes\PovLive.pov\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\PovLive.exe,0"; Tasks: associar
Root: HKA; Subkey: "Software\Classes\PovLive.pov\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PovLive.exe"" ""%1"""; Tasks: associar

[Run]
Filename: "{app}\PovLive.exe"; Description: "{cm:LaunchProgram,PovLive}"; Flags: nowait postinstall skipifsilent
