@echo off
cd /d C:\control\starter
:loop
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find /I "pythonw" >nul
if %errorlevel% neq 0 (
    start /MIN "" "C:\control\starter\venv\Scripts\pythonw.exe" "C:\control\starter\starter.py"
)
timeout /t 30 /nobreak >nul
goto loop
