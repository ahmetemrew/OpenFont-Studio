@echo off
chcp 65001 > nul
title OpenFont Studio
echo ===================================================
echo   OpenFont Studio Başlatılıyor...
echo   URL: http://localhost:5000
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [BILGI] Sanal ortam bulunamadi, olusturuluyor...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
)

echo Tarayici aciliyor...
start http://localhost:5000

echo Sunucu baslatiliyor (Durdurmak icin Ctrl + C yapabilirsiniz)...
.venv\Scripts\python builder/font_editor.py
pause
