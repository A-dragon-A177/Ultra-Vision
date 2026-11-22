@echo off
title Vision Host Tools Server
cd /d "C:\Vision\host_tools"

echo [Vision] Starting host tools server on port 8081...
echo [Vision] Docker calls this via http://host.docker.internal:8081

REM Activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
)

REM Install deps if needed
python -m pip install -q -r requirements.txt

REM Start server
python server.py

pause
