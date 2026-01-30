@echo off
setlocal
cd /d "%~dp0"

title TellTims Survey Automator

echo ===========================================
echo   TellTims Survey Automator - PC Launcher
echo ===========================================
echo.

REM 1. Check/Create Virtual Environment
if not exist "venv" (
    echo [Setup] Creating Python virtual environment...
    python -m venv venv
)

REM 2. Activate Virtual Environment
call venv\Scripts\activate

REM 3. Install/Update Dependencies
echo [Setup] Checking dependencies...
pip install -r requirements.txt > nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Failed to install dependencies. Running verbose install...
    pip install -r requirements.txt
    pause
    exit /b
)

REM 4. Run the App
echo.
echo [System] Starting App on Port 5001...
echo [System] Access local: http://localhost:5001
echo.

python app.py

pause
