@echo off
title Insurance Dashboard — Backend
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

echo Starting backend on http://localhost:8000 ...
%PYTHON_EXE% dashboard\backend\main.py
pause
