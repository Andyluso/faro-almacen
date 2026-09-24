import hashlib
import io
import os
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from backend.persistence import restore_archive, ensure_database
from backend import database, reliability


def seed(tmp_path, monkeypatch):
    database_path = tmp_path / 'seed.db'
    monkeypatch.setattr(database, 'DB_PATH', str(database_path))
    database.init_db()
    database.create_store_task('Preservar al reiniciar')
    content = io.BytesIO()
    with zipfile.ZipFile(content, 'w') as z:
        z.write(database_path, 'backend/inventario.db')
        z.writestr('backend/uploads/photo.jpg', b'original')
    return content.getvalue()


def test_restore_once_preserves_existing_volume_files_and_later_edits(tmp_path, monkeypatch):
    content = seed(tmp_path, monkeypatch)
    uploads = tmp_path / 'uploads'
    uploads.mkdir()
    (uploads / 'photo.jpg').write_bytes(b'newer')
    target = uploads / '.faro' / 'inventario.db'
    assert restore_archive(content, hashlib.sha256(content).hexdigest(), target, uploads)
    assert (uploads / 'photo.jpg').read_bytes() == b'newer'
    with sqlite3.connect(target) as conn:
        conn.execute("INSERT INTO store_tasks(title) VALUES ('Cambio nuevo')")
    with patch('backend.private_backup.private_client', side_effect=AssertionError('No download on restart')):
        ensure_database(target, uploads)
    assert not restore_archive(b'invalid', 'wrong', target, uploads)
    with sqlite3.connect(target) as conn:
        assert conn.execute("SELECT COUNT(*) FROM store_tasks WHERE title='Cambio nuevo'").fetchone()[0] == 1


def test_required_bootstrap_does_not_silently_create_empty_database(tmp_path, monkeypatch):
    monkeypatch.setenv('FARO_REQUIRE_BOOTSTRAP', '1')
    monkeypatch.delenv('FARO_BOOTSTRAP_ARCHIVE', raising=False)
    target = tmp_path / 'data' / 'inventario.db'
    with pytest.raises(RuntimeError):ensure_database(target, tmp_path / 'uploads')
    assert not target.exists()


def test_corruption_and_traversal_fail_before_restoring(tmp_path, monkeypatch):
    content = seed(tmp_path, monkeypatch)
    target = tmp_path / 'data' / 'inventario.db'
    with pytest.raises(RuntimeError):restore_archive(content, 'incorrect', target, tmp_path / 'uploads')
    assert not target.exists()
    bad = io.BytesIO(content)
    with zipfile.ZipFile(bad, 'a') as z:z.writestr('backend/uploads/../../outside.txt', b'bad')
    content = bad.getvalue()
    with pytest.raises(RuntimeError):restore_archive(content, hashlib.sha256(content).hexdigest(), target, tmp_path / 'uploads')
    assert not target.exists()
    assert not (tmp_path / 'outside.txt').exists()


def test_backup_does_not_recursively_include_private_database_and_backups(tmp_path, monkeypatch):
    uploads = tmp_path / 'uploads'
    private = uploads / '.faro'
    private.mkdir(parents=True)
    monkeypatch.setattr(database, 'DB_PATH', str(private / 'inventario.db'))
    monkeypatch.setenv('FARO_UPLOADS_DIR', str(uploads))
    database.init_db()
    (uploads / 'photo.jpg').write_bytes(b'photo')
    archive = reliability.make_backup(force=True)
    archive = reliability.make_backup(force=True)
    with zipfile.ZipFile(archive) as z:
        assert sorted(z.namelist()) == ['backend/inventario.db', 'backend/uploads/photo.jpg']


@pytest.mark.parametrize('path', ['.faro/inventario.db', '.faro/backups/copy.zip', 'nested/.env'])
def test_private_volume_files_never_served(tmp_path, path):
    from backend.main import PublicUploads
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'private')
    app = FastAPI()
    app.mount('/uploads', PublicUploads(directory=str(tmp_path)))
    assert TestClient(app).get('/uploads/' + path).status_code == 404
