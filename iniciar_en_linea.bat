@echo off
cd /d "%~dp0"
title FARO - Flujo de Almacen y Reorden Operativo
color 0b
echo ================================================================
echo           FARO - FLUJO DE ALMACEN Y REORDEN OPERATIVO
echo ================================================================
echo.
echo Iniciando servidor backend en el puerto 8000...
start /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
echo Esperando que el servidor inicie...
timeout /t 3 /nobreak >nul
echo.
echo ================================================================
echo   Generando enlace web publico seguro (HTTPS)...
echo   Cualquier persona puede entrar desde su celular con datos 4G/5G
echo   sin necesidad de estar conectado al mismo Wi-Fi.
echo ================================================================
echo.
echo.
"%~dp0cloudflared.exe" tunnel --url http://localhost:8000 --logfile "%~dp0tunnel.log"

