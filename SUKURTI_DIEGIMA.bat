@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Brezly - diegimo programos kurimas
echo ==================================================
echo   Brezly_Setup.exe kurimas (uztruks 2-5 min.)
echo   Reikia: Python ir interneto rysio
echo ==================================================
echo.

python --version >nul 2>&1 && (set PY=python) || (set PY=py)
%PY% --version >nul 2>&1 || (
    echo Python nerastas. Idiek is python.org ir pazymek "Add Python to PATH".
    pause & exit /b 1
)

echo [1/3] Diegiami PyInstaller ir pywin32...
%PY% -m pip install --upgrade pyinstaller pywin32 || goto klaida

echo.
echo [2/3] Kuriamas Brezly.exe...
rem testavimas.json NEdedamas - naudotoju versijoje testavimo irankiu nera
%PY% -m PyInstaller --noconfirm --clean --windowed --name Brezly --icon brezly.ico ^
  --contents-directory . --add-data "brezly.html;." --add-data "brezly.ico;." --add-data "praktika;praktika" ^
  --hidden-import win32timezone brezly.py || goto klaida

echo.
echo [3/3] Kuriama diegimo programa...
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" (
    echo Inno Setup nerastas - diegiu ji per winget...
    winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
    set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
    if not exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
)
if not exist "%ISCC%" (
    echo Nepavyko rasti Inno Setup. Atsisiusk is jrsoftware.org/isdl.php, idiek ir paleisk si faila dar karta.
    pause & exit /b 1
)
"%ISCC%" diegimas\brezly.iss || goto klaida

rmdir /s /q build 2>nul
del /q Brezly.spec 2>nul
echo.
echo ==================================================
echo   Sukurta: isvestis\Brezly_Setup.exe
echo   Si viena faila gali duoti draugams.
echo ==================================================
explorer isvestis
pause
exit /b 0

:klaida
echo.
echo Ivyko klaida - nufotografuok si langa.
pause
exit /b 1
