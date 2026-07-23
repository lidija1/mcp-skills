@echo off
setlocal

set PYTHON_EXE=python
if exist ".venv\Scripts\python.exe" set PYTHON_EXE=.venv\Scripts\python.exe

set /p FRAMEWORK_ROOT=Framework root path (Enter for current folder): 
if "%FRAMEWORK_ROOT%"=="" set FRAMEWORK_ROOT=%CD%

set /p FRAMEWORK_TYPE=Framework type: auto, java, python, generic (Enter for auto): 
if "%FRAMEWORK_TYPE%"=="" set FRAMEWORK_TYPE=auto

set /p LOB=LOB key to scan (Enter for all): 
set OUTPUT=docs\framework_knowledge.json

if "%LOB%"=="" (
  %PYTHON_EXE% tools\build_framework_knowledge.py --root "%FRAMEWORK_ROOT%" --framework-type "%FRAMEWORK_TYPE%" --output "%OUTPUT%"
) else (
  %PYTHON_EXE% tools\build_framework_knowledge.py --root "%FRAMEWORK_ROOT%" --framework-type "%FRAMEWORK_TYPE%" --lob "%LOB%" --output "%OUTPUT%"
)

if errorlevel 1 (
  echo.
  echo Framework knowledge build failed.
  pause
  exit /b 1
)

echo.
echo Knowledge file: %OUTPUT%
pause
