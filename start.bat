@echo off
chcp 65001 > nul
title Smart Pantry Manager [Port 8019]
echo ========================================================
echo   SMART PANTRY MANAGER [PORT 8019]
echo ========================================================

if exist "C:\Python313\python.exe" (
    set "PY=C:\Python313\python.exe"
) else (
    set "PY=python"
)

echo [INFO] Проверка и освобождение порта 8019...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8019" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

echo [INFO] Запуск веб-сервера на http://localhost:8019 ...
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8019"

cd /d "%~dp0"
"%PY%" -m uvicorn main:app --host 127.0.0.1 --port 8019
pause
