@echo off
title Market Analyzer
cd /d "%~dp0"
start /b python app.py
timeout /t 4 /nobreak >nul
start http://localhost:5001
echo.
echo Market Analyzer calisiyor... Kapatmak icin bu pencereyi kapatin.
echo.
pause
taskkill /f /im python.exe >nul 2>&1
