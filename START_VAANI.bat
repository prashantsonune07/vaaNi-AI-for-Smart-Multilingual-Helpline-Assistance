@echo off
title VaaNi - 1092 AI Helpline
color 0A

echo.
echo  ================================================
echo       VaaNi - 1092 AI Helpline Starting...
echo  ================================================
echo.
echo  Opening dashboard in browser...
start "" "C:\Users\prash\Desktop\vaani\frontend\index.html"

echo  Starting AI server...
echo  Keep this window open while using the app!
echo  Press Ctrl+C to stop.
echo.

cd /d "C:\Users\prash\Desktop\vaani\backend"
python main.py

pause
