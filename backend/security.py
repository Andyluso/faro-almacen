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
    async def dispatch(self, request, call_next):
        from .team_store import connection, digest
        from starlette.responses import RedirectResponse
        path = request.url.path
        if path == '/healthz':
            return JSONResponse({'status': 'ok', 'version': 'team-2026-09'})
        public = path in ('/login','/activate','/auth.css','/auth.js','/sw.js') or (path in ('/api/auth/login','/api/auth/activate') and request.method == 'POST')
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin = request.headers.get('origin')
            if (origin and urlsplit(origin).netloc != request.headers.get('host')) or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail':'Origen no permitido'},status_code=403)
        if not public:
            token = request.cookies.get('faro_session','')
            with connection() as conn:
                row = conn.execute('SELECT u.*,s.csrf FROM app_sessions s JOIN app_users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.active=1',(digest(token),time.time())).fetchone() if token else None
            if not row:
                if path.startswith('/api/'):
                    return JSONResponse({'detail':'Inicia sesión para continuar'},status_code=401,headers={'Cache-Control':'no-store'})
                return RedirectResponse('/login',status_code=303,headers={'Cache-Control':'no-store'})
            request.state.user = dict(row)
            request.state.csrf = row['csrf']
            if request.method not in ('GET','HEAD','OPTIONS') and not hmac.compare_digest(request.headers.get('x-csrf-token',''),row['csrf']):
                return JSONResponse({'detail':'La sesión necesita actualizarse. Recarga la página.'},status_code=403)
            if path == '/api/system/backup' and row['role'] != 'admin':
                return JSONResponse({'detail':'Solo el administrador puede descargar respaldos'},status_code=403)
            if row['role'] == 'employee':
                allowed = path.startswith('/api/team/') or path.startswith('/api/auth/') or path in ('/','/workspace','/workspace.html','/workspace.css','/workspace.js','/mobile-menu.css','/mobile-menu.js')
                if not allowed:
                    return JSONResponse({'detail':'No tienes permiso para esta sección'},status_code=403)
            # The new agenda and scheduling API are authoritative. Legacy write routes stay closed.
            if path.startswith(('/api/schedules','/api/tasks')) and request.method not in ('GET','HEAD'):
                return JSONResponse({'detail':'Usa la nueva Agenda y Horarios para guardar cambios'},status_code=409)
        response = await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        if path in ('/','/login','/activate','/workspace','/workspace.html'):
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response
