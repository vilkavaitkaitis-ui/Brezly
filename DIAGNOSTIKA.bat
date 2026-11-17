@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Brezly paleidimas su klaidu rodymu.
echo.
if not exist brezly.py (
  echo Ieskau brezly.py aplanke Atsisiuntimai...
  for /r "%USERPROFILE%\Downloads" %%f in (brezly.py) do if exist "%%f" cd /d "%%~dpf"
)
if not exist brezly.py (
  echo NERASTA. Isskleisk ZIP: desiniu peles mygtuku - "Isskleisti viska", tada bandyk vel.
  pause
  exit /b
)
echo Aplankas: %CD%
python --version >nul 2>&1 && (set PY=python) || (set PY=py)
%PY% --version
%PY% -c "import win32com.client; print('pywin32 OK')"
%PY% -X utf8 brezly.py
echo.
echo Programa baigesi. Jei virsuje yra Traceback - nufotografuok.
if exist klaida.txt type klaida.txt
pause
