from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from datetime import timedelta
import json
import re
from .team_store import connection,user,manager,parse_date,today,now,event

router=APIRouter(prefix='/api/team')
DAY_NAMES=['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']
OLD_DAYS=['Lun','Mar','Mie','Jue','Vie','Sab','Dom']

def time_minutes(value):
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value or ''):raise HTTPException(422,'Hora inválida')
    h,m=map(int,value.split(':'));return h*60+m
def week_date(value):
    result=parse_date(value)
    if result.weekday()!=0:raise HTTPException(422,'La semana debe iniciar un lunes')
    return result

@router.get('/roster')
def roster(request:Request):
    user(request)
    with connection() as c:return [dict(r) for r in c.execute('SELECT id,name,role,is_active FROM employees WHERE is_active=1 ORDER BY name')]

class Petition(BaseModel):
    employee_id:int|None=None
    date_from:str
    date_to:str
    kind:str='preference'
    day_off:bool=False
    earliest_start:str=''
    latest_end:str=''
    note:str=Field(default='',max_length=1000)
class Decision(BaseModel):
    status:str
    note:str=Field(default='',max_length=1000)

@router.get('/requests')
def petitions(request:Request,week:str|None=None):
    actor=user(request)
    sql='SELECT r.*,e.name AS employee_name,u.name AS decided_name FROM app_requests r JOIN employees e ON e.id=r.employee_id LEFT JOIN app_users u ON u.id=r.decided_by WHERE 1=1';params=[]
    if actor['role']=='employee':sql+=' AND r.created_by=?';params.append(actor['id'])
    if week:
        start=week_date(week);sql+=' AND r.date_from<=? AND r.date_to>=?';params.extend([(start+timedelta(days=6)).isoformat(),week])
    with connection() as c:return [dict(r) for r in c.execute(sql+' ORDER BY r.date_from,r.id DESC',params)]

@router.post('/requests')
def create_petition(body:Petition,request:Request):
    actor=user(request);eid=body.employee_id if actor['role'] in ('admin','manager') else actor['employee_id']
    if not eid:raise HTTPException(422,'Tu cuenta necesita estar vinculada a un colaborador')
    start,end=parse_date(body.date_from),parse_date(body.date_to)
    if end<start or (end-start).days>90:raise HTTPException(422,'Elige un periodo de hasta 90 días')
    if body.kind not in ('preference','restriction'):raise HTTPException(422,'Tipo de petición inválido')
    if body.earliest_start:time_minutes(body.earliest_start)
    if body.latest_end:time_minutes(body.latest_end)
    if body.earliest_start and body.latest_end and body.earliest_start>=body.latest_end:raise HTTPException(422,'Revisa la franja horaria')
    if not body.day_off and not body.earliest_start and not body.latest_end and not body.note.strip():raise HTTPException(422,'Describe la petición')
    with connection() as c:
        if not c.execute('SELECT 1 FROM employees WHERE id=? AND is_active=1',(eid,)).fetchone():raise HTTPException(422,'Colaborador no disponible')
        rid=c.execute('INSERT INTO app_requests(employee_id,created_by,date_from,date_to,kind,day_off,earliest_start,latest_end,note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(eid,actor['id'],body.date_from,body.date_to,body.kind,int(body.day_off),body.earliest_start,body.latest_end,body.note.strip(),now())).lastrowid
        event(c,actor['id'],'request_created','request',rid)
    return {'id':rid,'status':'pending'}

@router.post('/requests/{rid}/decision')
def decide_petition(rid:int,body:Decision,request:Request):
    actor=user(request)
    if actor['role']!='manager':raise HTTPException(403,'Solo la encargada puede aprobar o rechazar peticiones')
    if body.status not in ('approved','rejected','revoked'):raise HTTPException(422,'Decisión inválida')
    with connection() as c:
        row=c.execute('SELECT * FROM app_requests WHERE id=?',(rid,)).fetchone()
        if not row:raise HTTPException(404,'Petición no encontrada')
        c.execute('UPDATE app_requests SET status=?,decided_by=?,decision_note=?,decided_at=? WHERE id=?',(body.status,actor['id'],body.note,now(),rid))
        event(c,actor['id'],'request_'+body.status,'request',rid,{'note':body.note})
    return {'ok':True}

class Shift(BaseModel):
    employee_id:int
    day:int=Field(ge=0,le=6)
    kind:str='regular'
    start:str='09:00'
    end:str='17:00'
    pause:int=Field(default=60,ge=0,le=180)
    note:str=Field(default='',max_length=300)
class Schedule(BaseModel):
    shifts:list[Shift]=Field(default_factory=list,max_length=700)
    notes:str=Field(default='',max_length=2000)
    revision:int=0
class Publish(BaseModel):
    revision:int
    acknowledge_warnings:bool=False

def normalize_shifts(c,body):
    known={r[0] for r in c.execute('SELECT id FROM employees WHERE is_active=1')};seen=set();result=[]
    for item in body.shifts:
        s=item.model_dump();key=(s['employee_id'],s['day'])
        if s['employee_id'] not in known or key in seen:raise HTTPException(422,'Colaborador o turno duplicado no válido')
        seen.add(key)
        if s['kind'] not in ('regular','reduction','saturday','sunday','holiday','off','comp'):raise HTTPException(422,'Tipo de turno inválido')
        if s['kind'] in ('off','comp'):s.update(start='',end='',pause=0,hours=0,ordinary=0,extra=0)
        else:
            minutes=time_minutes(s['end'])-time_minutes(s['start'])-s['pause']
            if minutes<=0 or minutes>720:raise HTTPException(422,'El turno debe durar entre 0 y 12 horas de trabajo')
            hours=round(minutes/60,2);extra=max(0,round(hours-7,2)) if s['kind'] in ('sunday','holiday') else 0
            s.update(hours=hours,ordinary=round(hours-extra,2),extra=extra)
        result.append(s)
    return result

def legacy_schedule(c,week):
    row=c.execute('SELECT * FROM schedules WHERE week_start_date=?',(week,)).fetchone()
    shifts=[]
    if row:
        for old in c.execute('SELECT * FROM schedule_shifts WHERE schedule_id=?',(row['id'],)):
            day=next((i for i,k in enumerate(OLD_DAYS) if k==old['day_of_week']),None)
            if day is None:continue
            hours=old['hours'] or 0;kind='off' if hours==0 else 'saturday' if day==5 else 'sunday' if day==6 else 'reduction' if hours==6 else 'regular'
            shifts.append({'employee_id':old['employee_id'],'day':day,'kind':kind,'start':old['start_time'],'end':old['end_time'],'pause':60 if hours else 0,'hours':hours,'ordinary':min(7,hours) if day==6 else hours,'extra':max(0,hours-7) if day==6 else 0,'note':old['notes']})
    return {'shifts':shifts,'notes':row['notes'] if row else ''}

def schedule_checks(c,week,data):
    start=week_date(week);by={(s['employee_id'],s['day']):s for s in data['shifts']};warnings=[];conflicts=[];totals=[]
    people=[dict(r) for r in c.execute('SELECT id,name FROM employees WHERE is_active=1 ORDER BY name')]
    prior=c.execute('SELECT published FROM app_schedule_versions WHERE week_start=?',((start-timedelta(days=7)).isoformat(),)).fetchone()
    previous=json.loads(prior['published']) if prior and prior['published'] else legacy_schedule(c,(start-timedelta(days=7)).isoformat())
    for p in people:
        shifts=[s for s in data['shifts'] if s['employee_id']==p['id']];ordinary=round(sum(s['ordinary'] for s in shifts),2);extra=round(sum(s['extra'] for s in shifts),2)
        totals.append({'employee_id':p['id'],'name':p['name'],'ordinary':ordinary,'extra':extra})
        if len(shifts)<7:warnings.append(p['name']+': faltan días por asignar')
        if ordinary!=42:warnings.append(f"{p['name']}: {ordinary:g} horas ordinarias; objetivo configurado 42")
        if sum(s['kind']=='reduction' for s in shifts)!=1:warnings.append(p['name']+': revisa el día de reducción')
        if not any(s['kind'] in ('off','comp') for s in shifts):warnings.append(p['name']+': no tiene descanso asignado')
        last_sunday=next((s for s in previous['shifts'] if s['employee_id']==p['id'] and s['day']==6),None)
        if last_sunday and last_sunday['hours']>0 and not any(s['kind']=='comp' for s in shifts):warnings.append(p['name']+': revisa el compensatorio por el domingo anterior')
        if last_sunday and last_sunday['hours']==0 and any(s['kind']=='comp' for s in shifts):warnings.append(p['name']+': descansó el domingo anterior; revisa el compensatorio')
        for s in shifts:
            expected={'regular':7,'reduction':6,'saturday':8,'sunday':8,'holiday':8}.get(s['kind'])
            if expected and s['hours']!=expected:warnings.append(f"{p['name']} · {DAY_NAMES[s['day']]}: {s['hours']:g} h; tipo de turno configurado {expected} h")
    coverage=[]
    for d in range(7):
        work=[s for s in data['shifts'] if s['day']==d and s['hours']>0];opening=sum(s['start']<='09:00' and s['end']>'09:00' for s in work);closing=sum(s['end']>='20:00' and s['start']<'20:00' for s in work)
        coverage.append({'day':d,'opening':opening,'closing':closing})
        if not opening or not closing:warnings.append(DAY_NAMES[d]+': revisar cobertura de '+('apertura' if not opening else 'cierre'))
    reqs=[dict(r) for r in c.execute("SELECT r.*,e.name AS employee_name FROM app_requests r JOIN employees e ON e.id=r.employee_id WHERE date_from<=? AND date_to>=? AND status IN ('pending','approved')",((start+timedelta(days=6)).isoformat(),week))]
    for r in reqs:
        if r['status']=='pending':warnings.append(r['employee_name']+': petición pendiente de decisión');continue
        if r['note'].strip():warnings.append(r['employee_name']+': revisa la nota de la petición aprobada #'+str(r['id'])+': '+r['note'])
        for d in range(7):
            day=(start+timedelta(days=d)).isoformat()
            if not r['date_from']<=day<=r['date_to']:continue
            s=by.get((r['employee_id'],d));bad=s and s['hours']>0 and (r['day_off'] or (r['earliest_start'] and s['start']<r['earliest_start']) or (r['latest_end'] and s['end']>r['latest_end']))
            if bad:
                message=f"{r['employee_name']} · {DAY_NAMES[d]}: el turno contradice la petición aprobada #{r['id']}"
                (conflicts if r['kind']=='restriction' else warnings).append(message)
    return {'warnings':list(dict.fromkeys(warnings)),'conflicts':conflicts,'totals':totals,'coverage':coverage,'requests':reqs}

@router.get('/schedules/{week}')
def get_week(week:str,request:Request):
    actor=user(request);week_date(week)
    with connection() as c:
        row=c.execute('SELECT * FROM app_schedule_versions WHERE week_start=?',(week,)).fetchone()
        if actor['role']=='employee':
            data=json.loads(row['published']) if row and row['published'] else None
            # Existing schedules become visible only after the manager explicitly publishes.
            return {'week':week,'data':data,'published_at':row['published_at'] if row else None,'readonly':True}
        data=json.loads(row['draft']) if row else legacy_schedule(c,week)
        return {'week':week,'data':data,'revision':row['revision'] if row else 0,'published_at':row['published_at'] if row else None,**schedule_checks(c,week,data)}

@router.post('/schedules/{week}/check')
def check_week(week:str,body:Schedule,request:Request):
    manager(request)
    with connection() as c:return schedule_checks(c,week,{'shifts':normalize_shifts(c,body),'notes':body.notes})

@router.put('/schedules/{week}')
def save_week(week:str,body:Schedule,request:Request):
    actor=manager(request);week_date(week)
    with connection() as c:
        c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM app_schedule_versions WHERE week_start=?',(week,)).fetchone()
        revision=row['revision'] if row else 0
        if body.revision!=revision:raise HTTPException(409,'Otra persona cambió esta semana. Recarga antes de guardar.')
        data={'shifts':normalize_shifts(c,body),'notes':body.notes};checks=schedule_checks(c,week,data)
        before=json.loads(row['draft']) if row else legacy_schedule(c,week)
        c.execute('INSERT INTO app_schedule_versions(week_start,draft,revision,updated_by,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(week_start) DO UPDATE SET draft=excluded.draft,revision=excluded.revision,updated_by=excluded.updated_by,updated_at=excluded.updated_at',(week,json.dumps(data),revision+1,actor['id'],now()))
        event(c,actor['id'],'schedule_saved','schedule',week,{'before':before,'after':data})
        return {'revision':revision+1,**checks}

@router.post('/schedules/{week}/publish')
def publish_week(week:str,body:Publish,request:Request):
    actor=manager(request);start=week_date(week)
    with connection() as c:
        c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM app_schedule_versions WHERE week_start=?',(week,)).fetchone()
        if not row or row['revision']!=body.revision:raise HTTPException(409,'Guarda el borrador actual antes de publicar')
        data=json.loads(row['draft']);checks=schedule_checks(c,week,data)
        if not data['shifts']:raise HTTPException(422,'El horario está vacío')
        if checks['conflicts']:raise HTTPException(409,{'message':'Resuelve las restricciones aprobadas antes de publicar','conflicts':checks['conflicts']})
        if checks['warnings'] and not body.acknowledge_warnings:raise HTTPException(409,{'message':'Revisa los avisos y confirma la publicación','warnings':checks['warnings']})
        c.execute('UPDATE app_schedule_versions SET published=draft,published_by=?,published_at=? WHERE week_start=?',(actor['id'],now(),week))
        existing=c.execute('SELECT id FROM schedules WHERE week_start_date=?',(week,)).fetchone()
        if existing:sid=existing['id'];c.execute('UPDATE schedules SET notes=? WHERE id=?',(data['notes'],sid))
        else:sid=c.execute('INSERT INTO schedules(week_start_date,week_end_date,title,notes) VALUES(?,?,?,?)',(week,(start+timedelta(days=6)).isoformat(),'Semana '+week,data['notes'])).lastrowid
        c.execute('DELETE FROM schedule_shifts WHERE schedule_id=?',(sid,))
        for s in data['shifts']:c.execute('INSERT INTO schedule_shifts(schedule_id,employee_id,day_of_week,shift_type,start_time,end_time,hours,notes) VALUES(?,?,?,?,?,?,?,?)',(sid,s['employee_id'],OLD_DAYS[s['day']],s['kind'],s['start'],s['end'],s['hours'],s['note']))
        event(c,actor['id'],'schedule_published','schedule',week,{'warnings_acknowledged':checks['warnings']})
    return {'ok':True}

@router.post('/schedules/{week}/suggest')
def suggest_week(week:str,request:Request):
    manager(request);start=week_date(week)
    with connection() as c:
        employees=[dict(r) for r in c.execute('SELECT id,name FROM employees WHERE is_active=1 ORDER BY id')]
        reqs=[dict(r) for r in c.execute("SELECT * FROM app_requests WHERE status='approved' AND kind='restriction' AND date_from<=? AND date_to>=?",((start+timedelta(days=6)).isoformat(),week))]
        result=[]
        for i,p in enumerate(employees):
            off=6 if i==start.isocalendar().week%max(1,len(employees)) else (i+start.isocalendar().week)%5
            reduction=next(d for d in range(5) if d!=off)
            for day in range(7):
                kind='off' if day==off else 'saturday' if day==5 else 'sunday' if day==6 else 'reduction' if day==reduction else 'regular'
                duration=0 if kind=='off' else 6 if kind=='reduction' else 8 if day>=5 else 7
                opening=(i+day)%2==0;begin=540 if opening else 1200-(duration+1)*60
                for r in reqs:
                    if r['employee_id']!=p['id'] or not r['date_from']<=(start+timedelta(days=day)).isoformat()<=r['date_to']:continue
                    if r['day_off']:kind='off';duration=0
                    if r['earliest_start']:begin=max(begin,time_minutes(r['earliest_start']))
                    if r['latest_end'] and begin+(duration+1)*60>time_minutes(r['latest_end']):duration=max(0,(time_minutes(r['latest_end'])-begin)/60-1)
                if duration<=0:kind='off';begin=540;duration=0
                end=min(1439,round(begin+(duration+1)*60))
                result.append(Shift(employee_id=p['id'],day=day,kind=kind,start=f'{begin//60:02d}:{begin%60:02d}',end=f'{end//60:02d}:{end%60:02d}'))
        data={'shifts':normalize_shifts(c,Schedule(shifts=result)),'notes':''}
        return {'data':data,**schedule_checks(c,week,data)}

@router.get('/history/{entity}/{entity_id}')
def history(entity:str,entity_id:str,request:Request):
    manager(request)
    if entity not in ('schedule','agenda','request','account'):raise HTTPException(422,'Historial no disponible')
    with connection() as c:return [dict(r) for r in c.execute('SELECT e.*,u.name AS actor_name FROM app_events e LEFT JOIN app_users u ON u.id=e.actor_id WHERE entity=? AND entity_id=? ORDER BY e.id DESC LIMIT 30',(entity,entity_id))]

from .agenda import router as agenda_router
router.include_router(agenda_router)
