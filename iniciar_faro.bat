@echo off
chcp 65001 >nul
title FARO - Servidor Local y Conexión Móvil
cls

echo ==============================================================================
echo 🧭 FARO - Flujo de Almacén y Reorden Operativo
echo ==============================================================================
echo Iniciando el sistema...
echo.

cd /d "%~dp0"

:: 1. Detener procesos huérfanos anteriores si existieran
taskkill /F /IM cloudflared.exe >nul 2>&1

:: 2. Iniciar servidor FastAPI (Backend) en segundo plano
echo [1/3] Iniciando servidor FastAPI (puerto 8000)...
start /B python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > nul 2>&1
timeout /t 3 /nobreak >nul

:: 3. Iniciar Túnel Cloudflare para conexión del celular
echo [2/3] Conectando túnel seguro HTTPS para tu celular...
if exist tunnel.log del /F /Q tunnel.log >nul 2>&1
start /B .\cloudflared.exe tunnel --url http://127.0.0.1:8000 --logfile tunnel.log > nul 2>&1

:: 4. Esperar a que el túnel genere la URL pública
echo [3/3] Obteniendo enlace móvil seguro...
python -c "
import time, re, urllib.request

for _ in range(20):
    time.sleep(1)
    try:
        content = open('tunnel.log', encoding='utf-8', errors='ignore').read()
        m = re.findall(r'https://[a-zA-Z0-9\-]+\.trycloudflare\.com', content)
        if m:
            url = m[-1]
            with open('tunnel_url.txt', 'w', encoding='utf-8') as f:
                f.write(url)
            print('\n' + '='*70)
            print('✅ SERVICIO FARO ACTIVO Y LISTO PARA USAR')
            print('='*70)
            print('💻 EN TU COMPUTADOR: http://localhost:8000')
            print('📱 EN TU CELULAR (PWA): ' + url)
            print('='*70)
            break
    except Exception:
        pass
"

:: 5. Abrir en el navegador local automáticamente
start http://localhost:8000

echo.
echo ==============================================================================
echo 📌 INSTRUCCIONES:
echo - Mantén esta ventana abierta mientras estés usando FARO.
echo - Para detener el servicio, simplemente cierra esta ventana o ejecuta detener_faro.bat
echo ==============================================================================
echo Presiona cualquier tecla para detener FARO...
pause >nul

:: Al presionar una tecla, cerrar todo limpiamente
call detener_faro.bat
