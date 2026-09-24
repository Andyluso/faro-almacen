"""Local recovery copies and durable change tracking. No automatic data export."""
import os
import sqlite3
import tempfile
import threading
import time
import zipfile
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from pathlib import Path

TABLES = ('audits', 'audit_items', 'catalog_photos', 'employees', 'schedules', 'schedule_shifts', 'store_tasks')
DB_PATH = None
_backup_lock = threading.Lock()
_worker = None
_last_backup_revision = None
_last_error = ''


@contextmanager
def connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize(path):
    global DB_PATH
    DB_PATH = str(path)
    with connection() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS sync_outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, table_name TEXT NOT NULL, operation TEXT NOT NULL, payload TEXT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS sync_meta (key TEXT PRIMARY KEY, value TEXT)')
        conn.execute("INSERT OR IGNORE INTO sync_meta VALUES ('revision', '0')")
        for table in TABLES:
            cols = [r['name'] for r in conn.execute(f'PRAGMA table_info({table})')]
            pk = 'reference' if table == 'catalog_photos' else 'id'
            for event in ('INSERT', 'UPDATE', 'DELETE'):
                prefix = 'OLD' if event == 'DELETE' else 'NEW'
                fields = [pk] if event == 'DELETE' else cols
                pairs = ', '.join(f"'{c}', {prefix}.{c}" for c in fields)
                operation = 'delete' if event == 'DELETE' else 'upsert'
                conn.execute(f'''CREATE TRIGGER IF NOT EXISTS outbox_{table}_{event}
                    AFTER {event} ON {table} BEGIN
                    INSERT INTO sync_outbox(table_name, operation, payload)
                    VALUES ('{table}', '{operation}', json_object({pairs}));
                    UPDATE sync_meta SET value = CAST(value AS INTEGER) + 1 WHERE key = 'revision';
                    END''')


def queue_file(path, remote_path):
    # Only local bookkeeping; no data is sent to another system.
    import json
    payload = json.dumps({'name': Path(path).name, 'remote_path': remote_path})
    with connection() as conn:
        conn.execute("INSERT INTO sync_outbox(table_name, operation, payload) VALUES ('files','file',?)", (payload,))
        conn.execute("UPDATE sync_meta SET value = CAST(value AS INTEGER)+1 WHERE key = 'revision'")


def status(probe=False):
    connected = False
    if probe and os.getenv('SUPABASE_URL'):
        try:
            from .cloud_adapter import get_client
            client = get_client()
            if client:
                client.table('audits').select('id').limit(1).execute()
                connected = True
        except Exception:
            pass
    with connection() as conn:
        pending = conn.execute('SELECT COUNT(*) FROM sync_outbox').fetchone()[0]
    from .private_backup import cloud_status
    cloud = cloud_status(probe=probe)
    return {'mode': 'sqlite', 'database': 'SQLite local', 'connected': connected,
            'supabase_connected': cloud['ready'] and cloud['last_backup'] is not None, 'cloud_reachable': connected,
            'pending_changes': pending, 'replication_enabled': cloud['enabled'],
            'last_cloud_backup': cloud['last_backup'],
            'checked_at': datetime.now(timezone.utc).isoformat(),
            'message': _last_error or cloud['message']}


def make_backup(force=False):
    global _last_backup_revision
    with _backup_lock:
        folder = Path(DB_PATH).parent / 'backups'
        folder.mkdir(exist_ok=True)
        with connection() as src:
            revision = src.execute("SELECT value FROM sync_meta WHERE key='revision'").fetchone()[0]
            previous = sorted(folder.glob('faro-*.zip'))
            if not force and revision == _last_backup_revision and previous:
                return str(previous[-1])
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            dest = folder / ('faro-' + stamp + '.zip')
            with tempfile.TemporaryDirectory(prefix='faro-backup-') as temp:
                snapshot = Path(temp) / 'inventario.db'
                with closing(sqlite3.connect(snapshot)) as target:
                    src.backup(target)
                with zipfile.ZipFile(dest.with_suffix('.tmp'), 'w', zipfile.ZIP_DEFLATED) as archive:
                    archive.write(snapshot, 'backend/inventario.db')
                    uploads = Path(os.getenv('FARO_UPLOADS_DIR', str(Path(DB_PATH).parent / 'uploads'))).resolve()
                    for file in uploads.rglob('*'):
                        relative = file.relative_to(uploads)
                        if file.is_file() and not any(part.startswith('.') for part in relative.parts) and not file.is_symlink():
                            archive.write(file, 'backend/uploads/' + file.relative_to(uploads).as_posix())
                dest.with_suffix('.tmp').replace(dest)
        _last_backup_revision = revision
        for old in sorted(folder.glob('faro-*.zip'))[:-20]:
            old.unlink()
        return str(dest)


def start_worker():
    global _worker
    if _worker and _worker.is_alive():
        return
    def run():
        global _last_error
        while True:
            try:
                make_backup()
                from .private_backup import upload_backup
                upload_backup()
                _last_error = ''
            except Exception as exc:
                _last_error = 'No se pudo crear el respaldo local (' + type(exc).__name__ + ').'
            time.sleep(30)
    _worker = threading.Thread(target=run, name='faro-backup', daemon=True)
    _worker.start()
