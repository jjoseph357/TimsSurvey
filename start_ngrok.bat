@echo off
echo Starting TellTims Survey Automator with Ngrok...
echo.

REM Start Flask in a new window
start "Flask Server" cmd /k "cd /d %~dp0 && python app.py"

REM Wait for Flask to start
timeout /t 3 /nobreak > nul

REM Start Ngrok
echo Starting Ngrok tunnel...
echo.
echo IMPORTANT: Copy the https:// URL that appears below
echo You can access the app from anywhere using that URL
echo.
pause
ngrok http 5001
