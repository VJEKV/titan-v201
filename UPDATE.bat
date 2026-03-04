@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   TITAN — Обновление с GitHub
echo ========================================
echo.

:: Сохранить .env перед обновлением
if exist titan-v200\backend\.env copy /y titan-v200\backend\.env _env_backup >nul

echo Скачивание обновления...
curl -L -o update.zip "https://github.com/VJEKV/titan-v201/archive/refs/heads/main.zip"
if not exist update.zip (
    echo ОШИБКА: не удалось скачать обновление
    pause
    exit /b
)

echo Распаковка...
if exist _temp rd /s /q _temp
tar -xf update.zip -C . 2>nul
if not exist titan-v201-main (
    mkdir _temp
    powershell -Command "Expand-Archive -Path 'update.zip' -DestinationPath '_temp' -Force"
    set "SRC=_temp\titan-v201-main"
) else (
    set "SRC=titan-v201-main"
)

echo Обновление файлов...
if exist titan-v200\backend rd /s /q titan-v200\backend
if exist titan-v200\frontend rd /s /q titan-v200\frontend

xcopy /s /e /y /q %SRC%\backend titan-v200\backend\
xcopy /s /e /y /q %SRC%\frontend titan-v200\frontend\

:: Восстановить .env после обновления
if exist _env_backup (
    copy /y _env_backup titan-v200\backend\.env >nul
    del _env_backup
)

:: Очистка
if exist _temp rd /s /q _temp
if exist titan-v201-main rd /s /q titan-v201-main
del update.zip

echo.
echo ========================================
echo   Готово! Запустите START.bat
echo ========================================
pause
exit
