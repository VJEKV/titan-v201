@echo off
cd /d "%~dp0"
echo ========================================
echo   TITAN Update from GitHub
echo ========================================
echo.

taskkill /f /im python.exe >nul 2>&1

:: Save .env before update
if exist titan-v200\backend\.env copy /y titan-v200\backend\.env _env_backup >nul

echo Downloading...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/VJEKV/titan-v201/archive/refs/heads/main.zip' -OutFile 'update.zip'"
if not exist update.zip (
    echo ERROR: Download failed
    pause
    exit /b
)

echo Extracting...
if exist _temp rd /s /q _temp
powershell -Command "Expand-Archive -Path 'update.zip' -DestinationPath '_temp' -Force"

echo Updating...
if exist titan-v200\backend rd /s /q titan-v200\backend
if exist titan-v200\frontend rd /s /q titan-v200\frontend

xcopy /s /e /y /q _temp\titan-v201-main\backend titan-v200\backend\
xcopy /s /e /y /q _temp\titan-v201-main\frontend titan-v200\frontend\

:: Restore .env after update
if exist _env_backup (
    copy /y _env_backup titan-v200\backend\.env >nul
    del _env_backup
)

rd /s /q _temp
del update.zip

echo.
echo ========================================
echo   Done! Run START.bat to launch.
echo ========================================
pause
exit
