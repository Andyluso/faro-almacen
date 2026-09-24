@echo off
cd /d "%~dp0"
title Seven Seven - Control de Inventario
color 0B

echo ========================================================
echo       SEVEN SEVEN - SISTEMA DE CONTROL DE INVENTARIO
echo ========================================================
echo Iniciando servidor local...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python en el sistema.
    echo Asegurate de tener Python instalado y anadido al PATH.
    pause
    exit /b
)

python run_server.py
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] El servidor se ha detenido.
    pause
)
