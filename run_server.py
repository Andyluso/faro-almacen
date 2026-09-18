import os
import socket
import webbrowser
import threading
import time
import uvicorn

def get_local_ip():
    """Detecta la IP local de la máquina en la red Wi-Fi o red local."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def open_browser(port):
    """Espera un instante para que Uvicorn levante y abre el navegador por defecto."""
    time.sleep(1.2)
    url = f"http://localhost:{port}"
    print(f"\n[+] Abriendo la aplicacion en tu navegador: {url}...")
    webbrowser.open(url)

def print_banner(local_ip, port):
    print("=" * 65)
    print("       SEVEN SEVEN - SISTEMA DE CONTROL DE INVENTARIO")
    print("              (Lecturas de Tienda y Bodega)")
    print("=" * 65)
    print(f" [PC] En este computador abre:\n      --> http://localhost:{port}")
    print(f"\n [CELULAR] Para usar con la camara de tu celular,")
    print(f"           conectate al mismo Wi-Fi y abre en Chrome/Safari:\n      --> http://{local_ip}:{port}")
    print("=" * 65)
    print(" Presiona Ctrl + C en esta ventana cuando desees apagar el sistema.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    port = 8000
    local_ip = get_local_ip()
    print_banner(local_ip, port)

    # Iniciar hilo para abrir el navegador automáticamente
    threading.Thread(target=open_browser, args=(port,), daemon=True).start()

    # Iniciar servidor FastAPI
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, log_level="info")
