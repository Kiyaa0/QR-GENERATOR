@echo off
title C++ Native Engine Compiler (MinGW GCC)
cd /d "%~dp0\.."

echo ========================================================
echo   Meng-compile C++ QR Native Core Engine
echo ========================================================

where g++ >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Compiler g++ tidak ditemukan di PATH sistem.
    pause
    exit /b 1
)

echo Meng-compile core/qr_native.dll ...
g++ -O3 -shared -std=c++17 -static -o core/qr_native.dll cpp/qr_native.cpp cpp/QrCode.cpp

echo Meng-compile core/qr_native.exe ...
g++ -O3 -std=c++17 -static -o core/qr_native.exe cpp/qr_native.cpp cpp/QrCode.cpp

if %ERRORLEVEL% equ 0 (
    echo [SUKSES] Berkas biner C++ berhasil di-compile ke folder core/
) else (
    echo [GAGAL] Terjadi kesalahan kompilasi.
)

pause
