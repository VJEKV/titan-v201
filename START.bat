@echo off
chcp 65001 >nul
cd /d "%~dp0titan-v200\backend"

:: Убить старый процесс если висит
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1

:: Проверить порт 8000 — если занят, подождать
netstat -ano | findstr ":8000 " >nul 2>&1
if %errorlevel%==0 (
    echo Порт 8000 занят, ожидание освобождения...
    ping -n 3 127.0.0.1 >nul
)

echo Запуск TITAN Аудит ТОРО...
start "" "%~dp0python\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000

:: Ожидание запуска сервера
ping -n 5 127.0.0.1 >nul

:: Открыть браузер
start http://127.0.0.1:8000
exit
