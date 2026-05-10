@echo off
cd /d C:\workspace\20260510_travel
set ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY_HERE
set UNSPLASH_ACCESS_KEY=YOUR_UNSPLASH_KEY_HERE
python generator.py >> logs\generator.log 2>&1
