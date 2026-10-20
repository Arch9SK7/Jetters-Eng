@echo off
cd /d "%~dp0"
python tools\spriteframes_gui.py
if errorlevel 1 (
  echo.
  echo Could not start the editor. Make sure Python 3 and Pillow are installed: pip install pillow
  pause
)
