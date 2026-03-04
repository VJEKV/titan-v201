@echo off
chcp 65001 >nul
cd /d "%~dp0titan-v200\backend"

echo Запуск TITAN Аудит ТОРО...
start "" "%~dp0python\pythonw.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000

:: Ожидание запуска сервера
ping -n 4 127.0.0.1 >nul

:: Открыть браузер
start http://127.0.0.1:8000
exit
