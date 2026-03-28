@echo off
cd /d "%~dp0"
if exist venv\Scripts\python.exe (
    echo Using venv...
    call venv\Scripts\activate.bat
    uvicorn main:app --reload --host 0.0.0.0
) else (
    echo No venv found. Run install.bat first, or using system Python...
    python -m uvicorn main:app --reload --host 0.0.0.0
)
pause
