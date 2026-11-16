#define AppVersion "1.1.0.1"
#define AppId "primeinc.PyMoviePrint.Explorer"

[Setup]
AppId={#AppId}
AppName=PyMoviePrint
AppVersion={#AppVersion}
AppPublisher=primeinc/PyMoviePrint
AppPublisherURL=https://github.com/primeinc/PyMoviePrint
AppSupportURL=https://github.com/primeinc/PyMoviePrint/issues
DefaultDirName={localappdata}\Programs\PyMoviePrint
DefaultGroupName=PyMoviePrint
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes
SetupMutex=PyMoviePrintExplorerLifecycle
AppMutex=Local\PyMoviePrintExplorerRunning
OutputDir=..\dist
OutputBaseFilename=PyMoviePrint-Setup
Compression=lzma2
SolidCompression=yes
SetupLogging=yes
SetupIconFile=PyMoviePrint.ico
UninstallDisplayIcon={app}\PyMoviePrint.exe
WizardStyle=modern

[Files]
Source: "..\dist\PyMoviePrint\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "PyMoviePrint.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\PyMoviePrint"; Filename: "{app}\PyMoviePrint.exe"; IconFilename: "{app}\PyMoviePrint.ico"

[Registry]
; These keys are not unconditionally deleted. The uninstall callback compares
; exact values before removal to preserve keys another program has changed.
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Create video contact sheet"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\PyMoviePrint.ico"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Document"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mp4\shell\PyMoviePrint.ContactSheet\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PyMoviePrint.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Create video contact sheet"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\PyMoviePrint.ico"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Document"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mkv\shell\PyMoviePrint.ContactSheet\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PyMoviePrint.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Create video contact sheet"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\PyMoviePrint.ico"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Document"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.mov\shell\PyMoviePrint.ContactSheet\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PyMoviePrint.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Create video contact sheet"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\PyMoviePrint.ico"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Document"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.avi\shell\PyMoviePrint.ContactSheet\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PyMoviePrint.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wmv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Create video contact sheet"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wmv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\PyMoviePrint.ico"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wmv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Document"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.wmv\shell\PyMoviePrint.ContactSheet\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PyMoviePrint.exe"" ""%1"""
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MUIVerb"; ValueData: "Create video contact sheet"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\PyMoviePrint.ico"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flv\shell\PyMoviePrint.ContactSheet"; ValueType: string; ValueName: "MultiSelectModel"; ValueData: "Document"
Root: HKCU; Subkey: "Software\Classes\SystemFileAssociations\.flv\shell\PyMoviePrint.ContactSheet\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PyMoviePrint.exe"" ""%1"""

[Code]
const
  VerbName = 'PyMoviePrint.ContactSheet';
  Prefix = 'Software\Classes\SystemFileAssociations\';
  LifecycleMutex = 'PyMoviePrintExplorerLifecycle';

function ExtensionByIndex(Index: Integer): String;
begin
  case Index of
    0: Result := '.mp4';
    1: Result := '.mkv';
    2: Result := '.mov';
    3: Result := '.avi';
    4: Result := '.wmv';
    5: Result := '.flv';

  else Result := '';
  end;
end;

function VerbKey(const Extension: String): String;
begin
  Result := Prefix + Extension + '\shell\' + VerbName;
end;

function ExpectedCommand: String;
begin
  Result := '"' + ExpandConstant('{app}\PyMoviePrint.exe') + '" "%1"';
end;

function ExpectedIcon: String;
begin
  Result := ExpandConstant('{app}\PyMoviePrint.ico');
end;

function LegacyVerbMatches(const Extension: String): Boolean;
var
  Key, Command, Menu, Model: String;
begin
  Key := VerbKey(Extension);
  Result := (not RegValueExists(HKCU, Key, 'Icon')) and
    RegQueryStringValue(HKCU, Key + '\command', '', Command) and
    RegQueryStringValue(HKCU, Key, 'MUIVerb', Menu) and
    RegQueryStringValue(HKCU, Key, 'MultiSelectModel', Model) and
    (Command = ExpectedCommand) and
    (Menu = 'Create video contact sheet') and (Model = 'Document');
end;

function VerbMatches(const Extension: String): Boolean;
var
  Key, Command, Menu, Model, Icon: String;
begin
  Key := VerbKey(Extension);
  Result := RegQueryStringValue(HKCU, Key + '\command', '', Command) and
    RegQueryStringValue(HKCU, Key, 'MUIVerb', Menu) and
    RegQueryStringValue(HKCU, Key, 'MultiSelectModel', Model) and
    RegQueryStringValue(HKCU, Key, 'Icon', Icon) and
    (Icon = ExpectedIcon) and
    (Command = ExpectedCommand) and
    (Menu = 'Create video contact sheet') and (Model = 'Document');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Index: Integer;
  Extension: String;
begin
  Result := '';
  for Index := 0 to 5 do
  begin
    Extension := ExtensionByIndex(Index);
    if RegKeyExists(HKCU, VerbKey(Extension)) and (not VerbMatches(Extension)) and (not LegacyVerbMatches(Extension)) then
    begin
      Result := 'Explorer action for ' + Extension +
        ' is already owned or modified by another installer. Remove the older action before installing.';
      Exit;
    end;
  end;
end;

function InitializeUninstall: Boolean;
begin
  Result := not CheckForMutexes(LifecycleMutex);
  if Result then CreateMutex(LifecycleMutex)
  else MsgBox('Another PyMoviePrint setup or uninstall is running. Close it first.', mbError, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Index: Integer;
  Extension, Key: String;
begin
  if CurUninstallStep <> usPostUninstall then Exit;
  if FileExists(ExpandConstant('{app}\PyMoviePrint.exe')) then
  begin
    Log('Application files remain: preserving Explorer verbs for retry.');
    Exit;
  end;
  for Index := 0 to 5 do
  begin
    Extension := ExtensionByIndex(Index);
    Key := VerbKey(Extension);
    if VerbMatches(Extension) then
    begin
      if not RegDeleteKeyIncludingSubkeys(HKCU, Key) then
        Log('Could not delete Explorer verb: ' + Key);
    end
    else if RegKeyExists(HKCU, Key) then
      Log('Preserved changed Explorer verb: ' + Key);
  end;
end;
