#ifndef AppVersion
  #error AppVersion must be defined by the build script.
#endif

#define AppName "Book Manager"
#define AppPublisher "daikya"
#define AppExeName "BookManager.exe"
#define AppIdValue "{{0E99B7C8-54CB-4D31-9DE3-F36E2B6F2A8C}"

[Setup]
AppId={#AppIdValue}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\BookManager
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible
OutputDir=..\..\dist\installer
OutputBaseFilename=BookManager-{#AppVersion}-windows-x64-setup
SetupIconFile=..\..\assets\windows\book_manager.ico
UninstallDisplayIcon={app}\{#AppExeName}
VersionInfoVersion={#AppVersion}
VersionInfoTextVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Installer
VersionInfoProductName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern dynamic
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加アイコン:"; Flags: unchecked

[Files]
Source: "..\..\dist\BookManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Book Managerを起動する"; Flags: nowait postinstall skipifsilent
