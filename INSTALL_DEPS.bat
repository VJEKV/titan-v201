@echo off
chcp 65001 >nul
echo ========================================
echo   TITAN-5 — установка новых зависимостей
echo ========================================
echo.

cd /d "%~dp0"

:: Убедимся, что python.exe есть
if not exist "python\python.exe" (
    echo ОШИБКА: не найден python\python.exe рядом с BAT-файлом
    pause
    exit /b 1
)

:: Обновим pip
echo [1/2] Обновление pip...
"python\python.exe" -m pip install --upgrade pip

:: Установка всех зависимостей из requirements.txt
echo.
echo [2/2] Установка требований (duckdb, pyarrow, scipy + существующие)...
"python\python.exe" -m pip install -r "titan-v200\backend\requirements.txt"

echo.
echo ========================================
echo   Готово! Запустите START.bat
echo ========================================
pause
exit
