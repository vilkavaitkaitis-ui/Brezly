@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Brezly Pilotas - .exe kurimas
echo ==========================================
echo   Brezly Pilotas - .exe programos kurimas
echo   (reikia interneto, uztrunka 1-3 min.)
echo ==========================================
echo.

python --version >nul 2>&1 && (set PY=python) || (set PY=py)
%PY% --version >nul 2>&1 || (
    echo Python nerastas. Idiek Python is python.org ir pazymek "Add Python to PATH".
    pause
    exit /b
)

echo Diegiami reikalingi paketai...
%PY% -m pip install --upgrade pyinstaller pywin32
if errorlevel 1 (
    echo Nepavyko idiegti paketu. Patikrink interneto rysi.
    pause
    exit /b
)

echo.
echo Kuriamas "Brezly Pilotas.exe" (programa su langu)...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --icon robotas.ico --name "Brezly Pilotas" programa.py
if errorlevel 1 goto klaida

echo.
echo Kuriamas "Brezly Pilotas konsole.exe" (meniu konsoleje)...
%PY% -m PyInstaller --noconfirm --clean --onefile --console --icon robotas.ico --name "Brezly Pilotas konsole" meniu.py
if errorlevel 1 goto klaida

echo.
echo Kuriamas "Brezly.exe" (mokymosi programa)...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --icon brezly.ico --name "Brezly" brezly.py
if errorlevel 1 goto klaida


copy /y "dist\Brezly.exe" . >nul
copy /y "dist\Brezly Pilotas.exe" . >nul
copy /y "dist\Brezly Pilotas konsole.exe" . >nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

echo.
echo Sukurta: "Brezly Pilotas.exe", "Brezly Pilotas konsole.exe" ir "Brezly.exe" siame aplanke.
echo .exe failai turi likti siame aplanke - salia ui.html, brezly.html ir .txt failu.
echo.
echo Dabar sukursiu nuorodas ant darbalaukio...
call IDIEGTI.bat
exit /b

:klaida
echo.
echo Kuriant .exe ivyko klaida - pasiziurek pranesimus auksciau.
pause
exit /b
