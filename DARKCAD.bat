@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0darkcad.py" (
    echo.
    echo  Nerandu darkcad.py salia sio failo.
    echo  Greiciausiai ZIP failas neisskleistas.
    echo  Spausk ant ZIP desiniu peles mygtuku - "Isskleisti viska" ^(Extract All^),
    echo  tada isskleistame aplanke paleisk DARKCAD.bat.
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

rem DarkCAD be juodo konsoles lango
where pythonw >nul 2>&1 && (start "" pythonw darkcad.py) || (start "" pyw darkcad.py)
