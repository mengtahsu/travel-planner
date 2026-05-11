@echo off
cd /d C:\workspace\20260510_travel
if not exist logs mkdir logs
python generator.py 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath logs\generator.log"
echo.
echo Done! Press any key to close...
pause > nul
