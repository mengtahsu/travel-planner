@echo off
cd /d C:\workspace\20260510_travel
if not exist logs mkdir logs
python generator.py >> logs\generator.log 2>&1
