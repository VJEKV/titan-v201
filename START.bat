@echo off
cd /d "%~dp0"

:: Create hidden launcher
echo Set WshShell = CreateObject("WScript.Shell") > "%~dp0_run.vbs"
echo WshShell.CurrentDirectory = "%~dp0titan-v200\backend" >> "%~dp0_run.vbs"
echo WshShell.Run """%~dp0python\python.exe"" -m uvicorn main:app --host 127.0.0.1 --port 8000", 0, False >> "%~dp0_run.vbs"

:: Run hidden
wscript "%~dp0_run.vbs"

:: Wait for server
ping -n 4 127.0.0.1 >nul

:: Open browser
start http://127.0.0.1:8000

:: Cleanup and exit
del "%~dp0_run.vbs"
exit
