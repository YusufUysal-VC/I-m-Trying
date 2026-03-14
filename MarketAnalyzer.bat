@echo off
title Market Analyzer
cd /d "%~dp0"
start http://localhost:5001
python app.py
pause
