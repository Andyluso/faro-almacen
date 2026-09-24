"""Restore the private deployment seed once; subsequent starts use the volume."""
import hashlib
import io
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

TABLES = {'audits', 'audit_items', 'catalog_photos', 'employees', 'schedules', 'schedule_shifts', 'store_tasks'}


def restore_archive(content, expected_sha, database_path, uploads_path):
    database_path = Path(database_path)
    if database_path.exists():
        return False
    if not expected_sha or hashlib.sha256(content).hexdigest() != expected_sha:
        raise RuntimeError('El respaldo inicial no pasó la comprobación de integridad')
    uploads_path = Path(uploads_path).resolve()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        # Validate every path before writing anything. Never restore private state as an upload.
        for entry in archive.infolist():
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or '\\' in entry.filename or any(p in ('.', '..') or p.startswith('.') for p in path.parts):
                raise RuntimeError('Ruta no permitida en el respaldo')
            if entry.filename != 'backend/inventario.db' and not entry.filename.startswith('backend/uploads/'):
                raise RuntimeError('Contenido no permitido en el respaldo')
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=database_path.parent, prefix='restore-') as folder:
            snapshot = Path(folder) / 'inventario.db'
            snapshot.write_bytes(archive.read('backend/inventario.db'))
            conn = sqlite3.connect(snapshot)
            try:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not TABLES.issubset(tables) or conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or conn.execute('PRAGMA foreign_key_check').fetchall():
                    raise RuntimeError('Base de datos inicial incompleta o dañada')
            finally:
                conn.close()
            for entry in archive.infolist():
                if entry.is_dir() or not entry.filename.startswith('backend/uploads/'):
                    continue
                relative = entry.filename[len('backend/uploads/'):]
                target = (uploads_path / relative).resolve()
                if not target.is_relative_to(uploads_path):
                    raise RuntimeError('Ruta fuera del almacenamiento')
                target.parent.mkdir(parents=True, exist_ok=True)
                # Existing volume files take precedence over the initial recovery copy.
                if not target.exists():
                    target.write_bytes(archive.read(entry))
            snapshot.replace(database_path)
    return True


def ensure_database(database_path, uploads_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    object_name = os.getenv('FARO_BOOTSTRAP_ARCHIVE', '')
    if not object_name:
        if os.getenv('FARO_REQUIRE_BOOTSTRAP') == '1':
            raise RuntimeError('Falta el respaldo privado inicial; no se creará una base vacía')
        return
    from .private_backup import private_client
    client, bucket = private_client()
    content = client.storage.from_(bucket).download(object_name)
    restore_archive(content, os.getenv('FARO_BOOTSTRAP_SHA256', ''), path, uploads_path)
