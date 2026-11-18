@echo off
chcp 65001 > nul
title Smart Pantry Manager [Port 8019]
echo ========================================================
echo   SMART PANTRY // INVENTORY & RECIPE RECOMMENDATIONS
echo ========================================================
echo [INFO] Проверка и установка зависимостей...
python -m pip install -r requirements.txt --quiet
echo [INFO] Запуск FastAPI веб-сервера на http://localhost:8019 ...
start http://localhost:8019
python -m uvicorn main:app --host 0.0.0.0 --port 8019
pause
