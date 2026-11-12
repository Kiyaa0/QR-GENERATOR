@echo off
title Menjalankan Desktop QR Code Generator...
cd /d "%~dp0"
if exist "venv\Scripts\python.exe" (
    start "" "venv\Scripts\pythonw.exe" main.py
) else (
    echo [ERROR] Virtual Environment belum ditemukan.
    echo Silakan buat venv atau jalankan instalasi terlebih dahulu.
    pause
)
