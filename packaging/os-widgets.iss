#define MyAppName "OS Widgets"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Comet Suite"
#define MyAppURL "https://github.com/Comet-Suite/os-widgets-windows"
#define MyAppExeName "OS-Widgets.exe"

[Setup]
AppId={{F28194A7-365E-4BB1-A896-75E77BCA9D28}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\OS Widgets
DefaultGroupName=OS Widgets
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\release
OutputBaseFilename=OS-Widgets-{#MyAppVersion}-Windows-x64-Setup
SetupIconFile=..\assets\os-widgets.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
MinVersion=10.0
VersionInfoVersion=1.2.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=OS Widgets Windows installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion=1.2.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "autostart"; Description: "Start OS Widgets when I sign in"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\OS-Widgets.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\motivational-quotes.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\packaging\reset-on-next-launch"; DestDir: "{localappdata}\OS Widgets"; DestName: ".reset-on-next-launch"; Flags: ignoreversion

[Icons]
Name: "{group}\OS Widgets"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\Uninstall OS Widgets"; Filename: "{uninstallexe}"
Name: "{autodesktop}\OS Widgets"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\OS Widgets"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch OS Widgets"; Flags: nowait postinstall skipifsilent
