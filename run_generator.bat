@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
cd /d C:\workspace\20260510_travel
if not exist logs mkdir logs
python generator.py 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath logs\generator.log"
if "%SESSIONNAME%"=="Console" (
    echo.
    echo Done! Press any key to close...
    pause > nul
)
