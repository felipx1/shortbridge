@echo off
REM Double-click this to run the ShortBridge download agent once.
REM Downloads whatever's pending (up to 5 videos), uploads it, exits.
REM Run again any time you want to pull down more.
cd /d "%~dp0..\.."
".venv\Scripts\python.exe" "scripts\agent\shortbridge_agent.py"
pause
