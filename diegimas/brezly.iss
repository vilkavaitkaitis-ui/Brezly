; Brėžly diegimo programa (Inno Setup 6)
; Surenkama per SUKURTI_DIEGIMA.bat arba GitHub (.github/workflows/brezly-diegimas.yml).
; Prieš tai PyInstaller sukuria aplanką dist\Brezly su Brezly.exe.

#ifndef Versija
  #define Versija "0.8"
#endif

[Setup]
AppId={{6B1E7A52-3C4D-4F0B-9B57-B2E21A0C7D11}
AppName=Brėžly
AppVersion={#Versija}
AppVerName=Brėžly {#Versija}
AppPublisher=Brėžly
AppComments=Tavo braižymo mokymosi draugas. Veikia su AutoCAD. Nepriklausoma programa, nesusijusi su Autodesk, Inc.
DefaultDirName={localappdata}\Programs\Brezly
DefaultGroupName=Brėžly
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\isvestis
OutputBaseFilename=Brezly_Setup
SetupIconFile=..\brezly.ico
UninstallDisplayIcon={app}\Brezly.exe
UninstallDisplayName=Brėžly
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "lt"; MessagesFile: "compiler:Default.isl"

[Messages]
SetupAppTitle=Brėžly diegimas
SetupWindowTitle=Brėžly diegimas
WelcomeLabel1=Sveiki! Įdiegsiu Brėžly
WelcomeLabel2=Brėžly - tavo braižymo mokymosi draugas: tu braižai AutoCAD'e, o Brėžly veda žingsnis po žingsnio, tikrina ir padeda.%n%nAdministratoriaus teisių nereikia, užtruks kelias sekundes.
ButtonNext=&Toliau >
ButtonBack=< &Atgal
ButtonCancel=Atšaukti
ButtonInstall=&Įdiegti
ButtonFinish=&Baigti
ButtonYes=&Taip
ButtonNo=&Ne
ReadyLabel1=Viskas paruošta
ReadyLabel2a=Spausk „Įdiegti“.
SelectTasksLabel2=Ką dar padaryti?
WizardSelectTasks=Papildomai
WizardReady=Pasiruošta diegti
WizardInstalling=Diegiama
InstallingLabel=Palauk, diegiamas Brėžly...
FinishedHeadingLabel=Brėžly įdiegtas!
FinishedLabel=Brėžly paruoštas. Prieš mokydamasis atsidaryk AutoCAD (pilną, ne LT versiją).
ClickFinish=Spausk „Baigti“.
ExitSetupTitle=Nutraukti diegimą
ExitSetupMessage=Diegimas nebaigtas. Tikrai nutraukti?
ConfirmUninstall=Pašalinti Brėžly? Tavo progresas (Dokumentai\Brezly) liks.
UninstalledAll=Brėžly pašalintas.

[Tasks]
Name: "darbalaukis"; Description: "Sukurti nuorodą darbalaukyje"; Flags: checkedonce

[InstallDelete]
; senesni diegimai (CADet ir .bat diegimas)
Type: files; Name: "{userdesktop}\CADet.lnk"
Type: files; Name: "{userprograms}\CADet.lnk"
Type: files; Name: "{userprograms}\Pasalinti CADet.lnk"
Type: files; Name: "{userprograms}\Pasalinti Brezly.lnk"
Type: filesandordirs; Name: "{localappdata}\CADet"
Type: filesandordirs; Name: "{localappdata}\Brezly"

[Files]
Source: "..\dist\Brezly\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\atnaujinimai_url.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\Brėžly"; Filename: "{app}\Brezly.exe"; Comment: "Tavo braižymo mokymosi draugas"
Name: "{autodesktop}\Brėžly"; Filename: "{app}\Brezly.exe"; Tasks: darbalaukis; Comment: "Tavo braižymo mokymosi draugas"

[Run]
Filename: "{app}\Brezly.exe"; Description: "Paleisti Brėžly dabar"; Flags: nowait postinstall skipifsilent
; automatinis atnaujinimas (tylus diegimas) - Brėžly vėl atsidaro pats
Filename: "{app}\Brezly.exe"; Flags: nowait skipifnotsilent
