[Setup]
AppName=AI Hand Gesture Racing Controller
AppVersion=2.0.0.dev0
DefaultDirName={autopf}\AI Hand Gesture Racing Controller
DefaultGroupName=AI Hand Gesture Racing Controller
OutputBaseFilename=AIHandGestureRacingController-Setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "..\dist\AIHandGestureRacingController.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config\*"; DestDir: "{app}\config"; Flags: recursesubdirs
Source: "..\plugins\*"; DestDir: "{app}\plugins"; Flags: recursesubdirs

[Icons]
Name: "{group}\AI Hand Gesture Racing Controller"; Filename: "{app}\AIHandGestureRacingController.exe"
