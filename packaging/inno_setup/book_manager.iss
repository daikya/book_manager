#ifndef AppVersion
  #error AppVersion must be defined by the build script.
#endif

#ifdef VerificationBuild
  #define AppName "Book Manager Verification"
  #define AppIdValue "{{9130FA9D-4E63-488F-AF66-2B8E41347BC5}"
#else
  #define AppName "Book Manager"
  #define AppIdValue "{{0E99B7C8-54CB-4D31-9DE3-F36E2B6F2A8C}"
#endif
#define AppPublisher "daikya"
#define AppExeName "BookManager.exe"

[Setup]
AppId={#AppIdValue}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
#ifdef VerificationBuild
DefaultDirName={localappdata}\Programs\BookManagerVerification
#else
DefaultDirName={localappdata}\Programs\BookManager
#endif
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible
OutputDir=..\..\dist\installer
#ifdef VerificationBuild
OutputBaseFilename=BookManager-Verification-{#AppVersion}-windows-x64-setup
#else
OutputBaseFilename=BookManager-{#AppVersion}-windows-x64-setup
#endif
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
#ifdef VerificationBuild
CloseApplications=no
#else
CloseApplications=yes
#endif
RestartApplications=no
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

#ifndef VerificationBuild
[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成する"; GroupDescription: "追加アイコン:"; Flags: unchecked

#endif

[Files]
Source: "..\..\dist\BookManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

#ifndef VerificationBuild
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Book Managerを起動する"; Flags: nowait postinstall skipifsilent

#endif
