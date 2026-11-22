@echo off
REM Runs Vision on a Windows laptop. Double-click this file. Keep the window open (minimise it).
cd /d "%~dp0"
if not exist .env (
  copy .env.example .env >nul
  echo Created .env. Open it in Notepad, fill in your keys, save, then double-click this file again.
  notepad .env
  pause
  exit /b
)
if not exist .venv (
  echo First run: setting up. This takes a minute...
  py -m venv .venv || python -m venv .venv
  .venv\Scripts\python -m pip install -q -r requirements.txt
)
:loop
echo Vision is starting. Close this window to stop it.
.venv\Scripts\python -m app.main
echo Vision stopped. Restarting in 10 seconds...
timeout /t 10 >nul
goto loop
