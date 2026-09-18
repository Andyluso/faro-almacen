@echo off
chcp 65001 >nul
title Detener FARO
cls

echo ==============================================================================
echo 🛑 Deteniendo servicios de FARO...
echo ==============================================================================

:: Detener cloudflared
taskkill /F /IM cloudflared.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  - Túnel Cloudflare detenido correctamente.
) else (
    echo  - Túnel Cloudflare no estaba en ejecución.
)

:: Detener uvicorn (proceso python que corre en puerto 8000)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
echo  - Servidor FastAPI detenido correctamente.

echo.
echo ✅ FARO se ha detenido por completo.
timeout /t 2 /nobreak >nul
exit
