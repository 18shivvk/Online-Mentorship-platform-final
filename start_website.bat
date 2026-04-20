@echo off
cd /d "%~dp0"
echo Opening MentorLink on http://127.0.0.1:5055
venv_new\Scripts\python.exe app.py
pause
