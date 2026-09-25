from fastapi import APIRouter,Request,HTTPException,UploadFile,File
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field
from datetime import timedelta
from pathlib import Path
import json,os,secrets,io
from PIL import Image
from .team_store import connection,user,manager,today,parse_date,now,event

router=APIRouter()

class Task(BaseModel):
    title:str=Field(min_length=1,max_length=150)
    description:str=Field(default='',max_length=4000)
    kind:str='task'
    audience:str='all'
    recipients:list[int]=Field(default_factory=list,max_length=100)
    completion:str='one'
    start_date:str
    due_time:str=''
    repeat_rule:str='once'
    weekdays:list[int]=Field(default_factory=list,max_length=7)
    end_date:str=''
    priority:str='normal'
    checklist:list[str]=Field(default_factory=list,max_length=20)
    revision:int=0
class Progress(BaseModel):
    status:str
    checked:list[int]=Field(default_factory=list,max_length=20)
    note:str=Field(default='',max_length=2000)
class Postpone(BaseModel):
    due_date:str
    due_time:str=''

def validate(c,body,actor):
    from .team_routes import time_minutes
    parse_date(body.start_date)
    if not body.title.strip():raise HTTPException(422,'Escribe un título para el recordatorio')
    if body.end_date and parse_date(body.end_date)<parse_date(body.start_date):raise HTTPException(422,'La fecha final debe ser posterior al inicio')
    if body.due_time:time_minutes(body.due_time)
    if body.kind not in ('task','notice') or body.audience not in ('all','selected','self') or body.completion not in ('one','each') or body.repeat_rule not in ('once','daily','weekly') or body.priority not in ('normal','high'):raise HTTPException(422,'Revisa los campos del recordatorio')
    if body.repeat_rule=='weekly' and (not body.weekdays or any(d not in range(7) for d in body.weekdays)):raise HTTPException(422,'Selecciona al menos un día de repetición')
    active={r[0] for r in c.execute('SELECT id FROM app_users WHERE active=1')}
    recipients=[actor['id']] if body.audience=='self' else sorted(set(body.recipients)) if body.audience=='selected' else []
    if body.audience!='all' and (not recipients or not set(recipients).issubset(active)):raise HTTPException(422,'Selecciona destinatarios activos')
    return {**body.model_dump(),'title':body.title.strip(),'recipients':recipients,'completion':'each' if body.kind=='notice' else body.completion,'checklist':[s.strip()[:200] for s in body.checklist if s.strip()]}

def fields(data):
    return (data['title'],data['description'],data['kind'],data['audience'],json.dumps(data['recipients']),data['completion'],data['start_date'],data['due_time'],data['repeat_rule'],json.dumps(sorted(set(data['weekdays']))),data['end_date'],data['priority'],json.dumps(data['checklist']))

def materialize(c):
    active=[r[0] for r in c.execute('SELECT id FROM app_users WHERE active=1')]
    for row in c.execute('SELECT * FROM app_agenda WHERE archived=0').fetchall():
        start=parse_date(row['start_date']);until=today()+timedelta(days=14)
        recipients=active if row['audience']=='all' else json.loads(row['recipients'])
        if row['repeat_rule']=='once':dates=[start]
        else:
            # Materialized past occurrences remain queryable; only fill the unprocessed interval.
            last=c.execute('SELECT MAX(occurrence_date) FROM app_occurrences WHERE agenda_id=?',(row['id'],)).fetchone()[0]
            cursor=max(start,min(today(),parse_date(last)+timedelta(days=1))) if last else max(start,today()-timedelta(days=366))
            until=max(until,start+timedelta(days=7))
            if row['end_date']:until=min(until,parse_date(row['end_date']))
            weekdays=json.loads(row['weekdays']);dates=[]
            while cursor<=until:
                if row['repeat_rule']=='daily' or cursor.weekday() in weekdays:dates.append(cursor)
                cursor+=timedelta(days=1)
        for d in dates:
            c.execute('INSERT OR IGNORE INTO app_occurrences(agenda_id,occurrence_date,due_date,due_time,recipients) VALUES(?,?,?,?,?)',(row['id'],d.isoformat(),d.isoformat(),row['due_time'],json.dumps(recipients)))
        if row['audience']=='all':
            encoded=json.dumps(recipients)
            c.execute('UPDATE app_occurrences SET recipients=? WHERE agenda_id=? AND occurrence_date>=? AND recipients<>?',(encoded,row['id'],today().isoformat(),encoded))

def occurrence(c,oid,actor):
    row=c.execute('SELECT o.*,a.title,a.description,a.kind,a.completion,a.checklist,a.archived,a.attachment,a.end_date FROM app_occurrences o JOIN app_agenda a ON a.id=o.agenda_id WHERE o.id=?',(oid,)).fetchone()
    if not row or row['archived']:raise HTTPException(404,'Recordatorio no disponible')
    if actor['role']=='employee' and actor['id'] not in json.loads(row['recipients']):raise HTTPException(404,'Recordatorio no disponible')
    return row

@router.get('/agenda')
def list_agenda(request:Request):
    actor=user(request)
    with connection() as c:
        materialize(c);people={r['id']:r['name'] for r in c.execute('SELECT id,name FROM app_users')};items=[]
        progress={}
        for r in c.execute('SELECT * FROM app_progress'):progress.setdefault(r['occurrence_id'],{})[r['user_id']]=dict(r)
        for row in c.execute('SELECT o.id AS occurrence_id,o.occurrence_date,o.due_date,o.due_time AS occurrence_time,o.recipients AS occurrence_recipients,a.* FROM app_occurrences o JOIN app_agenda a ON a.id=o.agenda_id WHERE a.archived=0 ORDER BY o.due_date,o.due_time,a.id'):
            members=json.loads(row['occurrence_recipients'])
            if actor['role']=='employee' and actor['id'] not in members:continue
            item=dict(row);states=progress.get(row['occurrence_id'],{});done=sum(states.get(uid,{}).get('status')=='done' for uid in members)
            item['done']=bool(members) and (done==len(members) if row['completion']=='each' else done>0)
            item['members']=[{'id':uid,'name':people.get(uid,'Cuenta anterior'),'status':states.get(uid,{}).get('status','pending'),'updated_at':states.get(uid,{}).get('updated_at'),'note':states.get(uid,{}).get('note','')} for uid in members]
            item['mine']=states.get(actor['id'],{'status':'pending','checked':'[]','note':''});item['mine']['checked']=json.loads(item['mine']['checked'])
            item['can_update']=actor['id'] in members
            item['checklist']=json.loads(item['checklist']);item['recipients']=json.loads(item['recipients']);item['weekdays']=json.loads(item['weekdays']);item.pop('occurrence_recipients',None)
            items.append(item)
        return {'today':today().isoformat(),'items':items}

@router.post('/agenda')
def create_task(body:Task,request:Request):
    actor=manager(request)
    with connection() as c:
        data=validate(c,body,actor)
        aid=c.execute('INSERT INTO app_agenda(title,description,kind,audience,recipients,completion,start_date,due_time,repeat_rule,weekdays,end_date,priority,checklist,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(*fields(data),actor['id'],now(),now())).lastrowid
        event(c,actor['id'],'created','agenda',aid);materialize(c)
    return {'id':aid}

@router.put('/agenda/{aid}')
def edit_task(aid:int,body:Task,request:Request):
    actor=manager(request)
    with connection() as c:
        c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM app_agenda WHERE id=? AND archived=0',(aid,)).fetchone()
        if not row:raise HTTPException(404,'Recordatorio no disponible')
        if body.revision!=row['revision']:raise HTTPException(409,'El recordatorio cambió. Recarga antes de editarlo.')
        if body.start_date!=row['start_date']:raise HTTPException(422,'Usa Posponer esta vez para cambiar la fecha de una tarea existente')
        data=validate(c,body,actor)
        # Existing progress is retained; only unstarted future instances are rebuilt.
        c.execute('DELETE FROM app_occurrences WHERE agenda_id=? AND occurrence_date>? AND NOT EXISTS(SELECT 1 FROM app_progress p WHERE p.occurrence_id=app_occurrences.id)',(aid,today().isoformat()))
        c.execute('UPDATE app_agenda SET title=?,description=?,kind=?,audience=?,recipients=?,completion=?,start_date=?,due_time=?,repeat_rule=?,weekdays=?,end_date=?,priority=?,checklist=?,revision=revision+1,updated_at=? WHERE id=?',(*fields(data),now(),aid))
        active=[r[0] for r in c.execute('SELECT id FROM app_users WHERE active=1')]
        c.execute('UPDATE app_occurrences SET recipients=? WHERE agenda_id=? AND occurrence_date>=?',(json.dumps(active if data['audience']=='all' else data['recipients']),aid,today().isoformat()))
        event(c,actor['id'],'edited','agenda',aid);materialize(c)
    return {'ok':True}

@router.delete('/agenda/{aid}')
def archive_task(aid:int,request:Request):
    actor=manager(request)
    with connection() as c:
        if not c.execute('SELECT 1 FROM app_agenda WHERE id=?',(aid,)).fetchone():raise HTTPException(404,'Recordatorio no disponible')
        c.execute('UPDATE app_agenda SET archived=1,revision=revision+1,updated_at=? WHERE id=?',(now(),aid));event(c,actor['id'],'archived','agenda',aid)
    return {'ok':True}

@router.post('/agenda/{aid}/restore')
def restore_task(aid:int,request:Request):
    actor=manager(request)
    with connection() as c:
        c.execute('UPDATE app_agenda SET archived=0,revision=revision+1,updated_at=? WHERE id=?',(now(),aid));event(c,actor['id'],'restored','agenda',aid)
    return {'ok':True}

@router.put('/occurrences/{oid}/progress')
def update_progress(oid:int,body:Progress,request:Request):
    actor=user(request)
    if body.status not in ('pending','doing','blocked','done'):raise HTTPException(422,'Estado inválido')
    with connection() as c:
        row=occurrence(c,oid,actor)
        if actor['id'] not in json.loads(row['recipients']):raise HTTPException(403,'Solo los destinatarios pueden actualizar su avance')
        checklist=json.loads(row['checklist']);checked=sorted(set(body.checked))
        if any(i<0 or i>=len(checklist) for i in checked):raise HTTPException(422,'Lista de pasos inválida')
        if body.status=='done' and row['kind']=='task' and len(checked)!=len(checklist):raise HTTPException(422,'Marca todos los pasos antes de finalizar')
        if body.status=='blocked' and not body.note.strip():raise HTTPException(422,'Explica la dificultad para que puedan ayudarte')
        if row['kind']=='notice' and body.status not in ('pending','done'):raise HTTPException(422,'El aviso se marca como leído')
        c.execute('INSERT INTO app_progress(occurrence_id,user_id,status,checked,note,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(occurrence_id,user_id) DO UPDATE SET status=excluded.status,checked=excluded.checked,note=excluded.note,updated_at=excluded.updated_at',(oid,actor['id'],body.status,json.dumps(checked),body.note,now()))
        event(c,actor['id'],'progress_'+body.status,'agenda',row['agenda_id'],{'occurrence':oid,'note':body.note})
    return {'ok':True}

@router.put('/occurrences/{oid}/postpone')
def postpone(oid:int,body:Postpone,request:Request):
    actor=manager(request);parse_date(body.due_date)
    from .team_routes import time_minutes
    if body.due_time:time_minutes(body.due_time)
    with connection() as c:
        row=occurrence(c,oid,actor)
        c.execute('UPDATE app_occurrences SET due_date=?,due_time=? WHERE id=?',(body.due_date,body.due_time,oid))
        event(c,actor['id'],'postponed','agenda',row['agenda_id'],{'occurrence':oid,**body.model_dump()})
    return {'ok':True}

def asset_folder():
    from .main import UPLOADS_DIR
    p=Path(UPLOADS_DIR)/'agenda-assets';p.mkdir(parents=True,exist_ok=True);return p

@router.post('/agenda/{aid}/photo')
async def attach_photo(aid:int,request:Request,file:UploadFile=File(...)):
    actor=manager(request)
    content=await file.read(5*1024*1024+1)
    if len(content)>5*1024*1024:raise HTTPException(413,'La foto debe pesar menos de 5 MB')
    try:
        image=Image.open(io.BytesIO(content));image.load();image=image.convert('RGB');image.thumbnail((1600,1600));stream=io.BytesIO();image.save(stream,format='JPEG',quality=85)
    except Exception:raise HTTPException(422,'Selecciona una imagen válida')
    with connection() as c:
        if not c.execute('SELECT 1 FROM app_agenda WHERE id=? AND archived=0',(aid,)).fetchone():raise HTTPException(404,'Recordatorio no disponible')
        name=secrets.token_hex(20)+'.jpg';(asset_folder()/name).write_bytes(stream.getvalue())
        c.execute('UPDATE app_agenda SET attachment=?,revision=revision+1,updated_at=? WHERE id=?',(name,now(),aid));event(c,actor['id'],'photo_added','agenda',aid)
    return {'ok':True}

@router.get('/occurrences/{oid}/photo')
def get_photo(oid:int,request:Request):
    actor=user(request)
    with connection() as c:row=occurrence(c,oid,actor)
    if not re_safe_photo(row['attachment']):raise HTTPException(404,'Foto no disponible')
    path=asset_folder()/row['attachment']
    if not path.is_file():raise HTTPException(404,'Foto no disponible')
    return FileResponse(path,media_type='image/jpeg')

def re_safe_photo(name):
    import re
    return bool(re.fullmatch(r'[a-f0-9]{40}\.jpg',name or ''))
