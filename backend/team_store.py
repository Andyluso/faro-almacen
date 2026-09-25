"""Additive migrations and shared helpers for individual accounts and store work."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from . import database

TRACKED = ('app_users','app_invites','app_requests','app_schedule_versions','app_agenda','app_occurrences','app_progress','app_events')

@contextmanager
def connection():
    conn = database.get_connection()
    try:
        with conn: yield conn
    finally: conn.close()

def now(): return datetime.now(timezone.utc).isoformat()
def today(): return datetime.now(ZoneInfo('America/Bogota')).date()
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt, hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
def check_password(password, row):
    if not row or not row['password_hash']: return False
    return hmac.compare_digest(password_hash(password, row['salt'])[1], row['password_hash'])
def user(request):
    value = getattr(request.state, 'user', None)
    if not value: raise HTTPException(401, 'Inicia sesión para continuar')
    return value
def manager(request):
    value = user(request)
    if value['role'] not in ('admin','manager'): raise HTTPException(403,'Esta función requiere permisos de gestión')
    return value
def event(conn, actor, action, entity, entity_id, details=None):
    conn.execute('INSERT INTO app_events(actor_id,action,entity,entity_id,details,created_at) VALUES(?,?,?,?,?,?)',
                 (actor,action,entity,str(entity_id),json.dumps(details or {},ensure_ascii=False),now()))
def public_user(row):
    return {key:row[key] for key in ('id','username','name','role','employee_id','active')}
def parse_date(value):
    try: return date.fromisoformat(value)
    except (ValueError,TypeError): raise HTTPException(422,'Fecha inválida')

def initialize():
    with connection() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS app_users(id INTEGER PRIMARY KEY,username TEXT NOT NULL UNIQUE COLLATE NOCASE,name TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','manager','employee')),employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL,salt TEXT NOT NULL DEFAULT '',password_hash TEXT NOT NULL DEFAULT '',active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS app_users_employee ON app_users(employee_id) WHERE employee_id IS NOT NULL;
        CREATE TABLE IF NOT EXISTS app_sessions(id INTEGER PRIMARY KEY,token_hash TEXT UNIQUE NOT NULL,user_id INTEGER NOT NULL REFERENCES app_users(id),csrf TEXT NOT NULL,expires_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS app_login_limits(id INTEGER PRIMARY KEY,bucket TEXT UNIQUE NOT NULL,count INTEGER NOT NULL,expires_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS app_invites(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES app_users(id),token_hash TEXT UNIQUE NOT NULL,kind TEXT NOT NULL,expires_at REAL NOT NULL,used_at TEXT,created_by INTEGER REFERENCES app_users(id),created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS app_requests(id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL REFERENCES employees(id),created_by INTEGER NOT NULL REFERENCES app_users(id),date_from TEXT NOT NULL,date_to TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('preference','restriction')),day_off INTEGER NOT NULL DEFAULT 0,earliest_start TEXT NOT NULL DEFAULT '',latest_end TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pending',decided_by INTEGER REFERENCES app_users(id),decision_note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,decided_at TEXT);
        CREATE INDEX IF NOT EXISTS app_requests_dates ON app_requests(date_from,date_to);
        CREATE TABLE IF NOT EXISTS app_schedule_versions(id INTEGER PRIMARY KEY,week_start TEXT UNIQUE NOT NULL,draft TEXT NOT NULL,published TEXT,revision INTEGER NOT NULL DEFAULT 1,updated_by INTEGER REFERENCES app_users(id),published_by INTEGER REFERENCES app_users(id),updated_at TEXT NOT NULL,published_at TEXT);
        CREATE TABLE IF NOT EXISTS app_agenda(id INTEGER PRIMARY KEY,legacy_id INTEGER UNIQUE,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',kind TEXT NOT NULL DEFAULT 'task',audience TEXT NOT NULL DEFAULT 'all',recipients TEXT NOT NULL DEFAULT '[]',completion TEXT NOT NULL DEFAULT 'one',start_date TEXT NOT NULL,due_time TEXT NOT NULL DEFAULT '',repeat_rule TEXT NOT NULL DEFAULT 'once',weekdays TEXT NOT NULL DEFAULT '[]',end_date TEXT NOT NULL DEFAULT '',priority TEXT NOT NULL DEFAULT 'normal',checklist TEXT NOT NULL DEFAULT '[]',attachment TEXT NOT NULL DEFAULT '',archived INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 1,created_by INTEGER REFERENCES app_users(id),created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS app_occurrences(id INTEGER PRIMARY KEY,agenda_id INTEGER NOT NULL REFERENCES app_agenda(id),occurrence_date TEXT NOT NULL,due_date TEXT NOT NULL,due_time TEXT NOT NULL DEFAULT '',recipients TEXT NOT NULL,UNIQUE(agenda_id,occurrence_date));
        CREATE INDEX IF NOT EXISTS app_occurrence_date ON app_occurrences(due_date);
        CREATE TABLE IF NOT EXISTS app_progress(id INTEGER PRIMARY KEY,occurrence_id INTEGER NOT NULL REFERENCES app_occurrences(id),user_id INTEGER NOT NULL REFERENCES app_users(id),status TEXT NOT NULL DEFAULT 'pending',checked TEXT NOT NULL DEFAULT '[]',note TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL,UNIQUE(occurrence_id,user_id));
        CREATE TABLE IF NOT EXISTS app_events(id INTEGER PRIMARY KEY,actor_id INTEGER REFERENCES app_users(id),action TEXT NOT NULL,entity TEXT NOT NULL,entity_id TEXT NOT NULL,details TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS app_event_entity ON app_events(entity,entity_id);
        ''')
        if not c.execute('SELECT 1 FROM app_users LIMIT 1').fetchone():
            from .security import credentials
            config = credentials()
            if not config: raise RuntimeError('Configura FARO_PASSWORD antes del primer inicio')
            username,salt,hashed=config
            if not salt: salt,hashed=password_hash(hashed)
            c.execute('INSERT INTO app_users(username,name,role,salt,password_hash,created_at) VALUES(?,?,?,?,?,?)',
                      (username.lower(),'Administrador','admin',salt,hashed,now()))
        # One-time import leaves every legacy row intact. Future task progress is per occurrence.
        marker=c.execute("SELECT value FROM sync_meta WHERE key='team_agenda_migrated'").fetchone()
        if not marker:
            days={'lunes':0,'martes':1,'miércoles':2,'miercoles':2,'jueves':3,'viernes':4,'sábado':5,'sabado':5,'domingo':6}
            for task in c.execute('SELECT * FROM store_tasks').fetchall():
                day=(task['day_of_week'] or '').lower();rule='daily' if day=='diario' else 'weekly' if day in days else 'once'
                c.execute('INSERT OR IGNORE INTO app_agenda(legacy_id,title,description,start_date,due_time,repeat_rule,weekdays,priority,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                          (task['id'],task['title'],task['description'] or '',task['due_date'] or today().isoformat(),task['due_time'] or '',rule,json.dumps([days[day]] if day in days else []),'high' if task['priority']=='Alta' else 'normal',now(),now()))
                if task['is_completed']:
                    c.execute('UPDATE app_agenda SET archived=1 WHERE legacy_id=? AND repeat_rule=\'once\'',(task['id'],))
            c.execute("INSERT INTO sync_meta(key,value) VALUES('team_agenda_migrated','1')")
        from . import reliability
        reliability.TABLES=tuple(dict.fromkeys(reliability.TABLES+TRACKED))
    reliability.initialize(database.DB_PATH)
