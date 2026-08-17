@echo off
cd /d %~dp0
echo ============================================
echo STARTER - Verbose Mode
echo ============================================
python -u starter.py 2>&1
pause
