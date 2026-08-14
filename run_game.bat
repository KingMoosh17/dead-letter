@echo off
setlocal
cd /d "%~dp0"
title Dead Letter

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py
    if %errorlevel%==0 goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python main.py
    if %errorlevel%==0 goto :eof
)

echo.
echo Dead Letter could not start.
echo Install Python 3.10 or newer from python.org and make sure Tcl/Tk is included.
echo Then run this file again.
echo.
pause
