"""Access protection for a single-store installation, including files and exports."""
import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from collections import OrderedDict
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


def credentials():
    password = os.getenv('FARO_PASSWORD', '')
    if len(password) >= 12:
        return os.getenv('FARO_USERNAME', 'admin'), None, password
    path = Path(__file__).parent / '.faro-access.json'
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        return data['username'], data['salt'], data['hash']
    return None


class AccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.failures = OrderedDict()

    async def dispatch(self, request, call_next):
        # An empty worker is safe to probe by hosting services without exposing data.
        if request.url.path == '/healthz':
            return JSONResponse({'status': 'ok'})
        # Deliver the cache-removal worker to existing installations before login.
        if request.url.path == '/sw.js' and request.method == 'GET':
            return await call_next(request)
        config = credentials()
        if not config:
            return JSONResponse({'detail': 'Configura el acceso con configurar_acceso.py antes de abrir FARO.'}, status_code=503)
        peer = request.client.host if request.client else 'unknown'
        count, until = self.failures.get(peer, (0, 0))
        if count >= 10 and time.monotonic() < until:
            return JSONResponse({'detail': 'Espera un minuto antes de volver a intentar.'}, status_code=429)
        valid = False
        header = request.headers.get('authorization', '')
        if header.startswith('Basic ') and len(header) < 4096:
            try:
                username, password = base64.b64decode(header[6:], validate=True).decode('utf-8').split(':', 1)
                expected_user, salt, expected = config
                actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex() if salt else password
                valid = hmac.compare_digest(username.encode(), expected_user.encode()) & hmac.compare_digest(actual.encode(), expected.encode())
            except (ValueError, UnicodeError):
                pass
        if not valid:
            if header:
                self.failures[peer] = (count + 1 if time.monotonic() < until else 1, time.monotonic() + 60)
                if len(self.failures) > 1024:
                    self.failures.popitem(last=False)
            return Response('Acceso restringido a FARO', status_code=401,
                            headers={'WWW-Authenticate': 'Basic realm="FARO", charset="UTF-8"', 'Cache-Control': 'no-store'})
        self.failures.pop(peer, None)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            # Match the host too when HTTPS is terminated by the local tunnel.
            if origin and urlsplit(origin).netloc != request.headers.get('host'):
                return JSONResponse({'detail': 'Origen no permitido'}, status_code=403)
            if request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Origen no permitido'}, status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        return response
