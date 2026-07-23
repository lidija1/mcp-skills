@echo off
title Insurance Dashboard — Frontend
cd /d "%~dp0frontend"
echo Starting frontend on http://localhost:5173 ...
call npm run build
call npm run serve
pause
