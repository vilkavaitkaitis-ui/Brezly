@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Brezly Pilotas

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

%PY% meniu.py
echo.
pause
