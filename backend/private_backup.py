"""Opt-in private ZIP backups of all seven modules and assets to the existing Supabase.

No uploads occur until FARO_PRIVATE_CLOUD_READY=1, a server secret is configured,
and the destination bucket is verified private. ZIP backups are the authoritative
recovery copy; legacy public tables are not used for synchronization.
"""
import base64
import json
import os
import sqlite3
import tempfile
import threading
import zipfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from . import reliability

_lock = threading.Lock()
_error = ''


def enabled():
    return os.getenv('FARO_PRIVATE_CLOUD_READY') == '1'


def server_key_configured():
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
    if key.startswith('sb_secret_'):
        return True
    try:
        return json.loads(base64.urlsafe_b64decode(key.split('.')[1] + '===')).get('role') == 'service_role'
    except (ValueError, IndexError):
        return False


def private_client():
    if not server_key_configured():
        raise RuntimeError('Falta la clave privada del servidor')
    from .cloud_adapter import get_client
    client = get_client()
    if client is None:
        raise RuntimeError('Sin conexión')
    bucket_name = os.getenv('SUPABASE_BACKUP_BUCKET', 'faro-backups')
    bucket = client.storage.get_bucket(bucket_name)
    is_public = bucket.get('public') if isinstance(bucket, dict) else getattr(bucket, 'public', None)
    if is_public is not False:
        raise RuntimeError('El destino de respaldo no es privado')
    return client, bucket_name


def cloud_status(probe=False):
    ready = False
    with reliability.connection() as conn:
        row = conn.execute("SELECT value FROM sync_meta WHERE key='last_cloud_backup'").fetchone()
    last = row[0] if row else None
    message = 'Respaldo local activo. Nube privada pendiente de configurar.'
    if enabled():
        if probe:
            try:
                private_client()
                ready = True
            except Exception:
                pass
        message = _error or ('Respaldo privado en nube comprobado.' if ready else 'No se pudo comprobar el respaldo privado en nube; los datos siguen guardados localmente.')
    return {'enabled': enabled(), 'ready': ready, 'last_backup': last, 'message': message}


def upload_backup():
    global _error
    if not enabled() or not _lock.acquire(blocking=False):
        return False
    try:
        client, bucket = private_client()
        path = Path(reliability.make_backup())
        with reliability.connection() as conn:
            previous = conn.execute("SELECT value FROM sync_meta WHERE key='cloud_archive'").fetchone()
        if previous and previous[0] == path.name:
            return True
        # Read the watermark from the snapshot, not the live DB: later edits stay pending.
        with tempfile.TemporaryDirectory(prefix='faro-watermark-') as folder:
            snapshot = Path(folder) / 'snapshot.db'
            with zipfile.ZipFile(path) as archive:
                snapshot.write_bytes(archive.read('backend/inventario.db'))
            with closing(sqlite3.connect(snapshot)) as conn:
                watermark = conn.execute('SELECT COALESCE(MAX(id),0) FROM sync_outbox').fetchone()[0]
        client.storage.from_(bucket).upload(path.name, path.read_bytes(),
                                            file_options={'upsert':'true', 'content-type':'application/zip'})
        with reliability.connection() as conn:
            conn.execute('DELETE FROM sync_outbox WHERE id<=?', (watermark,))
            conn.execute("INSERT OR REPLACE INTO sync_meta VALUES ('cloud_archive', ?)", (path.name,))
            conn.execute("INSERT OR REPLACE INTO sync_meta VALUES ('last_cloud_backup', ?)", (datetime.now(timezone.utc).isoformat(),))
        _error = ''
        return True
    except Exception as exc:
        _error = 'Respaldo en nube pendiente (' + type(exc).__name__ + '). Se reintentará automáticamente.'
        return False
    finally:
        _lock.release()
