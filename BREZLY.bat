@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0brezly.py" (
    echo.
    echo  Nerandu brezly.py salia sio failo.
    echo  Greiciausiai ZIP failas neisskleistas.
    echo  Spausk ant ZIP desiniu peles mygtuku - "Isskleisti viska" ^(Extract All^),
    echo  tada isskleistame aplanke paleisk BREZLY.bat.
    echo.
    pause
    exit /b
)

python --version >nul 2>&1 && (set PY=python) || (set PY=py)
%PY% --version >nul 2>&1 || (
    echo Python nerastas. Idiek Python is python.org ir pazymek "Add Python to PATH".
    pause
    exit /b
)
%PY% -c "import win32com.client" >nul 2>&1 || (
    echo Diegiamas pywin32 paketas, palauk...
    %PY% -m pip install pywin32
)

rem Brezly be juodo konsoles lango
where pythonw >nul 2>&1 && (start "" pythonw brezly.py) || (start "" pyw brezly.py)
