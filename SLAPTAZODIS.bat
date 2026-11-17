@echo off
chcp 65001 >nul
cd /d "%~dp0"
python testavimo_slaptazodis.py
pause
