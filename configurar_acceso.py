"""Run locally to set or change the store's shared access password."""
import getpass
import hashlib
import json
import secrets
from pathlib import Path

def save_access(username, password):
    if len(password) < 12:
        raise ValueError('La contraseña debe tener al menos 12 caracteres.')
    salt = secrets.token_bytes(16)
    data = {'username': username, 'salt': salt.hex(),
            'hash': hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1).hex()}
    path = Path(__file__).parent / 'backend' / '.faro-access.json'
    path.write_text(json.dumps(data), encoding='utf-8')

if __name__ == '__main__':
    username = input('Usuario [admin]: ').strip() or 'admin'
    password = getpass.getpass('Nueva contraseña (mínimo 12 caracteres): ')
    if password != getpass.getpass('Repetir contraseña: '):
        raise SystemExit('Las contraseñas no coinciden.')
    save_access(username, password)
    print('Acceso configurado. Reinicia FARO y entra con ese usuario y contraseña.')
