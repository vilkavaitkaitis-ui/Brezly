@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Brezly Pilotas - idiegimas
echo ==========================================
echo   Brezly Pilotas - nuorodos ant darbalaukio
echo   ir Start meniu
echo ==========================================
echo.

set "DIR=%~dp0"
set "ICO=%~dp0robotas.ico"

rem --- 1. Programa su langu ---
set "LNK=Brezly Pilotas.lnk"
set "ARGS="
set "TGT="
if exist "%DIR%Brezly Pilotas.exe" set "TGT=%DIR%Brezly Pilotas.exe"
if not defined TGT (
    for /f "delims=" %%i in ('where pythonw 2^>nul') do if not defined TGT set "TGT=%%i"
    if defined TGT set "ARGS="%DIR%programa.py""
)
if not defined TGT set "TGT=%DIR%PROGRAMA.bat"
call :nuoroda

rem --- 2. Meniu konsoleje (atsarginis) ---
set "LNK=Brezly Pilotas konsole.lnk"
set "ARGS="
if exist "%DIR%Brezly Pilotas konsole.exe" (
    set "TGT=%DIR%Brezly Pilotas konsole.exe"
) else (
    set "TGT=%DIR%PALEISTI.bat"
)
call :nuoroda

rem --- 3. Brezly - mokymosi programa ---
set "LNK=Brezly.lnk"
set "ARGS="
set "TGT="
set "ICO_SENAS=%ICO%"
set "ICO=%~dp0brezly.ico"
if exist "%DIR%Brezly.exe" set "TGT=%DIR%Brezly.exe"
if not defined TGT (
    for /f "delims=" %%i in ('where pythonw 2^>nul') do if not defined TGT set "TGT=%%i"
    if defined TGT set "ARGS="%DIR%brezly.py""
)
if not defined TGT set "TGT=%DIR%BREZLY.bat"
call :nuoroda
set "ICO=%ICO_SENAS%"

rem --- senos nuorodos (AutoCAD AI, CADet) pasalinimas ---
powershell -NoProfile -Command "foreach ($v in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) { foreach ($n in @('AutoCAD AI.lnk','AutoCAD AI konsole.lnk','AutoCAD AI langas.lnk','CADet.lnk','DarkCAD.lnk')) { Remove-Item -ErrorAction SilentlyContinue (Join-Path $v $n) } }"

echo.
echo Baigta! Ant darbalaukio ir Start meniu atsirado:
echo    Brezly                  - mokykis braizyti pats (rekomenduojama)
echo    Brezly Pilotas          - braizo uz tave, programa su langu
echo    Brezly Pilotas konsole  - meniu juodame lange (atsarginis)
echo.
echo  (darbalaukyje vardai rodomi su lietuviskomis raidemis)
echo.
echo Nuorodas istrinti: tiesiog istrink jas nuo darbalaukio ir is Start meniu.
pause
exit /b

:nuoroda
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$w = New-Object -ComObject WScript.Shell;" ^
  "foreach ($v in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {" ^
  "  $n = $env:LNK -replace 'Brezly', ('Br' + [char]0x117 + [char]0x17E + 'ly');" ^
  "  $s = $w.CreateShortcut((Join-Path $v $n));" ^
  "  $s.TargetPath = $env:TGT; $s.Arguments = [string]$env:ARGS;" ^
  "  $s.WorkingDirectory = $env:DIR; $s.IconLocation = $env:ICO;" ^
  "  $s.Description = 'Brezly - nepriklausoma programa, nesusijusi su Autodesk'; $s.Save() }"
if errorlevel 1 (
    echo   Nepavyko sukurti nuorodos %LNK%
) else (
    echo   Sukurta: %LNK%
)
exit /b
