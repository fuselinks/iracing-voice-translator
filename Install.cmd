@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto fail
echo Installation complete. Use Start.cmd.
pause
exit /b 0
:fail
echo Installation failed. Install Python 3.12 x64 with Tk and PATH enabled.
pause
exit /b 1
