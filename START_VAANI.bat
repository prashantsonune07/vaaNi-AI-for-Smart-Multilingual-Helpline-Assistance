@echo off
title VaaNi - 1092 AI Helpline
color 0A

echo.
echo  ================================================
echo       VaaNi - 1092 AI Helpline Starting...
echo  ================================================
echo.

cd /d "C:\Users\prash\Desktop\vaani\backend"

echo  Starting AI server... please wait 6 seconds...
echo  Keep this window open while using the app!
echo  Press Ctrl+C to stop.
echo.

start /b py main.py

timeout /t 6 /nobreak >nul

echo  Opening dashboard in browser...
start "" "http://localhost:8000"
echo  Done! Browser should open now.
echo.

pause
