@echo off
cd /d "%~dp0"
echo Creating virtual environment...
if not exist venv python -m venv venv
echo Installing dependencies (this may take a few minutes)...
call venv\Scripts\activate.bat
pip install -r requirements.txt
echo.
echo Done. Run start-backend.bat to start the server.
pause
