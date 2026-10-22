@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe goto missing
start "" .venv\Scripts\pythonw.exe run.py
exit /b
:missing
echo First run Install.cmd
pause
