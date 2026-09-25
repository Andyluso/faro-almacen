import secrets
import time
import re
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .team_store import connection, user, manager, public_user, check_password, password_hash, digest, event, now

router=APIRouter(prefix='/api')

class Login(BaseModel):
    username: str = Field(min_length=1,max_length=150)
    password: str = Field(min_length=1,max_length=256)
class Activate(BaseModel):
    token: str = Field(min_length=20,max_length=200)
    password: str = Field(min_length=12,max_length=256)
class Invite(BaseModel):
    username: str = Field(min_length=3,max_length=150)
    name: str = Field(min_length=2,max_length=100)
    role: str = 'employee'
    employee_id: int | None = None
class AccountEdit(BaseModel):
    active: bool
    role: str
class ChangePassword(BaseModel):
    current_password: str = Field(max_length=256)
    password: str = Field(min_length=12,max_length=256)

def allow_login(c,bucket):
    t=time.time();row=c.execute('SELECT * FROM app_login_limits WHERE bucket=?',(bucket,)).fetchone()
    if row and row['expires_at']>t and row['count']>=10: raise HTTPException(429,'Demasiados intentos. Espera 15 minutos.')
    c.execute('DELETE FROM app_login_limits WHERE expires_at<?',(t,))
    c.execute('INSERT INTO app_login_limits(bucket,count,expires_at) VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=count+1',(bucket,t+900))

@router.post('/auth/login')
def login(body: Login,request: Request):
    name=body.username.strip().lower()
    peer=request.client.host if request.client else 'unknown'
    with connection() as c: allow_login(c,'login:'+digest(peer+':'+name))
    with connection() as c:
        row=c.execute('SELECT * FROM app_users WHERE username=?',(name,)).fetchone()
        # Scrypt also runs for unknown accounts to avoid cheap account enumeration.
        valid=check_password(body.password,row)
        if not row: password_hash(body.password,'0'*32)
        if not valid or not row['active']: raise HTTPException(401,'Usuario o contraseña incorrectos')
        c.execute('DELETE FROM app_login_limits WHERE bucket=?',('login:'+digest(peer+':'+name),))
        c.execute('DELETE FROM app_sessions WHERE expires_at<?',(time.time(),))
        token=secrets.token_urlsafe(40);csrf=secrets.token_urlsafe(32)
        c.execute('INSERT INTO app_sessions(token_hash,user_id,csrf,expires_at) VALUES(?,?,?,?)',(digest(token),row['id'],csrf,time.time()+43200))
        event(c,row['id'],'login','account',row['id'])
        result=JSONResponse({'user':public_user(row),'csrf':csrf})
        import os
        secure=bool(os.getenv('RAILWAY_ENVIRONMENT_ID')) or request.url.scheme=='https'
        result.set_cookie('faro_session',token,httponly=True,secure=secure,samesite='lax',max_age=43200,path='/')
        return result

@router.get('/auth/me')
def me(request:Request):
    return {'user':public_user(user(request)),'csrf':request.state.csrf}

@router.post('/auth/logout')
def logout(request:Request):
    with connection() as c:c.execute('DELETE FROM app_sessions WHERE token_hash=?',(digest(request.cookies.get('faro_session','')),))
    result=JSONResponse({'ok':True});result.delete_cookie('faro_session',path='/');return result

@router.post('/auth/activate')
def activate(body:Activate,request:Request):
    with connection() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT i.*,u.active FROM app_invites i JOIN app_users u ON u.id=i.user_id WHERE token_hash=?',(digest(body.token),)).fetchone()
        if not row or row['used_at'] or row['expires_at']<time.time() or not row['active']: raise HTTPException(400,'Este enlace no está disponible. Solicita una nueva invitación.')
        salt,hashed=password_hash(body.password)
        c.execute('UPDATE app_users SET salt=?,password_hash=? WHERE id=?',(salt,hashed,row['user_id']))
        c.execute('UPDATE app_invites SET used_at=? WHERE user_id=? AND used_at IS NULL',(now(),row['user_id']))
        c.execute('DELETE FROM app_sessions WHERE user_id=?',(row['user_id'],))
        event(c,row['user_id'],'password_set','account',row['user_id'])
    return {'ok':True}

@router.post('/auth/password')
def change_password(body:ChangePassword,request:Request):
    actor=user(request)
    with connection() as c:
        row=c.execute('SELECT * FROM app_users WHERE id=?',(actor['id'],)).fetchone()
        if not check_password(body.current_password,row):raise HTTPException(400,'La contraseña actual no coincide')
        salt,hashed=password_hash(body.password)
        c.execute('UPDATE app_users SET salt=?,password_hash=? WHERE id=?',(salt,hashed,actor['id']))
        c.execute('DELETE FROM app_sessions WHERE user_id=?',(actor['id'],))
        c.execute('UPDATE app_invites SET used_at=? WHERE user_id=? AND used_at IS NULL',(now(),actor['id']))
        event(c,actor['id'],'password_changed','account',actor['id'])
    return {'ok':True}

@router.get('/team/people')
def people(request:Request):
    manager(request)
    with connection() as c:
        return [dict(r) for r in c.execute("SELECT id,name,username,role,employee_id,active,CASE WHEN password_hash='' THEN 'invited' ELSE 'active' END AS account_status FROM app_users ORDER BY name")]

def make_invite(c,uid,actor,kind):
    token=secrets.token_urlsafe(36)
    c.execute('UPDATE app_invites SET used_at=? WHERE user_id=? AND used_at IS NULL',(now(),uid))
    c.execute('INSERT INTO app_invites(user_id,token_hash,kind,expires_at,created_by,created_at) VALUES(?,?,?,?,?,?)',(uid,digest(token),kind,time.time()+86400*3,actor,now()))
    event(c,actor,'invite_created','account',uid)
    return {'activation_path':'/activate#'+token,'expires_in_days':3}

@router.post('/team/people')
def invite(body:Invite,request:Request):
    actor=manager(request)
    if body.role not in ('admin','manager','employee') or (actor['role']!='admin' and body.role!='employee'):raise HTTPException(403,'Solo el administrador puede asignar cargos de gestión')
    name=body.username.strip().lower()
    if len(body.name.strip())<2:raise HTTPException(422,'Escribe el nombre de la persona')
    if not re.fullmatch(r'[a-z0-9@._+\-]{3,150}',name):raise HTTPException(422,'Usa un correo o usuario sin espacios')
    with connection() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT 1 FROM app_users WHERE username=?',(name,)).fetchone():raise HTTPException(409,'Ese usuario ya existe')
        eid=body.employee_id
        if eid:
            if not c.execute('SELECT 1 FROM employees WHERE id=? AND is_active=1',(eid,)).fetchone():raise HTTPException(422,'Colaborador no disponible')
            if c.execute('SELECT 1 FROM app_users WHERE employee_id=?',(eid,)).fetchone():raise HTTPException(409,'Ese colaborador ya tiene una cuenta')
        elif body.role!='admin':
            eid=c.execute('INSERT INTO employees(name,role) VALUES(?,?)',(body.name,'Encargada' if body.role=='manager' else 'Asesor Comercial')).lastrowid
        uid=c.execute('INSERT INTO app_users(username,name,role,employee_id,created_at) VALUES(?,?,?,?,?)',(name,body.name.strip(),body.role,eid,now())).lastrowid
        return {'id':uid,**make_invite(c,uid,actor['id'],'activation')}

@router.post('/team/people/{uid}/invite')
def renew_invite(uid:int,request:Request):
    actor=manager(request)
    with connection() as c:
        row=c.execute('SELECT * FROM app_users WHERE id=? AND active=1',(uid,)).fetchone()
        if not row:raise HTTPException(404,'Cuenta no disponible')
        if actor['role']!='admin' and row['role']!='employee':raise HTTPException(403,'Solo el administrador puede recuperar esta cuenta')
        return make_invite(c,uid,actor['id'],'recovery')

@router.put('/team/people/{uid}')
def edit_account(uid:int,body:AccountEdit,request:Request):
    actor=manager(request)
    with connection() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM app_users WHERE id=?',(uid,)).fetchone()
        if not row:raise HTTPException(404,'Cuenta no disponible')
        if body.role not in ('admin','manager','employee'):raise HTTPException(422,'Cargo inválido')
        if actor['role']!='admin' and (row['role']!='employee' or body.role!='employee'):raise HTTPException(403,'No puedes modificar este cargo')
        if uid==actor['id'] and (not body.active or body.role!=row['role']):raise HTTPException(400,'No puedes retirar tu propio acceso de gestión')
        if row['role']=='admin' and (not body.active or body.role!='admin') and c.execute("SELECT COUNT(*) FROM app_users WHERE role='admin' AND active=1").fetchone()[0]<=1:raise HTTPException(400,'Debe quedar un administrador activo')
        c.execute('UPDATE app_users SET active=?,role=? WHERE id=?',(int(body.active),body.role,uid))
        c.execute('DELETE FROM app_sessions WHERE user_id=?',(uid,))
        if not body.active:c.execute('UPDATE app_invites SET used_at=? WHERE user_id=? AND used_at IS NULL',(now(),uid))
        event(c,actor['id'],'account_updated','account',uid,body.model_dump())
    return {'ok':True}
