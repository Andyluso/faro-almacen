import os,json,sqlite3,io,zipfile
from datetime import timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

os.environ.update(FARO_USERNAME='tester',FARO_PASSWORD='test-password-12345',SUPABASE_URL='',SUPABASE_KEY='',SUPABASE_SERVICE_ROLE_KEY='',FARO_PRIVATE_CLOUD_READY='0')
from backend import database as db
from backend import team_store as ts

PASSWORD='test-password-12345'

@pytest.fixture()
def env(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB_PATH',str(tmp_path/'inventario.db'))
    monkeypatch.setenv('FARO_UPLOADS_DIR',str(tmp_path/'uploads'))
    monkeypatch.delenv('FARO_BOOTSTRAP_ARCHIVE',raising=False)
    monkeypatch.delenv('FARO_REQUIRE_BOOTSTRAP',raising=False)
    from backend import main
    monkeypatch.setattr(main,'UPLOADS_DIR',str(tmp_path/'uploads'))
    monkeypatch.setattr(main,'EXCELS_DIR',str(tmp_path/'uploads/excels'))
    Path(main.EXCELS_DIR).mkdir(parents=True,exist_ok=True)
    db.init_db();ts.initialize();main.app.middleware_stack=None
    clients=[]
    def connect(username='tester'):
        http=TestClient(main.app);res=http.post('/api/auth/login',json={'username':username,'password':PASSWORD});assert res.status_code==200,res.text
        http.headers['X-CSRF-Token']=res.json()['csrf'];clients.append(http);return http
    admin=connect()
    def invite(name,role='employee',eid=None):
        res=admin.post('/api/team/people',json={'username':name,'name':name.title(),'role':role,'employee_id':eid});assert res.status_code==200,res.text
        token=res.json()['activation_path'].split('#')[1]
        http=TestClient(main.app);res2=http.post('/api/auth/activate',json={'token':token,'password':PASSWORD});assert res2.status_code==200,res2.text
        return res.json()['id'],connect(name)
    manager_id,lead=invite('encargada','manager',1)
    employee_id,employee=invite('asesora','employee',2)
    other_id,other=invite('bodega','employee',3)
    yield {'admin':admin,'manager':lead,'employee':employee,'other':other,'uid':employee_id,'other_uid':other_id,'manager_uid':manager_id,'app':main.app,'tmp':tmp_path,'invite':invite}
    for http in clients:http.close()

def task(env,**kwargs):
    body={'title':'Probar tarea','start_date':ts.today().isoformat(),'audience':'selected','recipients':[env['uid']],'completion':'each',**kwargs}
    res=env['manager'].post('/api/team/agenda',json=body);assert res.status_code==200,res.text
    result=env['manager'].get('/api/team/agenda').json()
    return next(t for t in result['items'] if t['id']==res.json()['id'] and t['occurrence_date']==body['start_date'])

def week():
    d=ts.today();return (d-timedelta(days=d.weekday())).isoformat()

def test_edit_recurrence_preserves_progress_and_refills_missing_dates(env):
    t=task(env,repeat_rule='daily')
    items=[x for x in env['manager'].get('/api/team/agenda').json()['items'] if x['id']==t['id']]
    last=items[-1]
    assert env['employee'].put(f"/api/team/occurrences/{last['occurrence_id']}/progress",json={'status':'doing'}).status_code==200
    body={k:t[k] for k in ('title','start_date','audience','recipients','completion','repeat_rule','revision')}
    body['title']='Tarea actualizada'
    assert env['manager'].put(f"/api/team/agenda/{t['id']}",json=body).status_code==200
    updated=[x for x in env['employee'].get('/api/team/agenda').json()['items'] if x['id']==t['id']]
    assert len(updated)==15
    assert updated[-1]['mine']['status']=='doing'
    body.update(revision=t['revision']+1,start_date=(ts.today()+timedelta(days=1)).isoformat())
    assert env['manager'].put(f"/api/team/agenda/{t['id']}",json=body).status_code==422

def test_login_page_has_no_browser_challenge_and_sessions_are_private(env):
    http=TestClient(env['app']);r=http.get('/');assert r.status_code==200 and 'Ingresa a FARO' in r.text
    r=http.get('/api/audits');assert r.status_code==401 and 'www-authenticate' not in r.headers
    login=http.post('/api/auth/login',json={'username':'tester','password':PASSWORD})
    assert 'HttpOnly' in login.headers['set-cookie'] and 'SameSite=lax' in login.headers['set-cookie']
    assert 'password_hash' not in login.text and 'salt' not in login.text
    assert http.get('/api/auth/me').status_code==200

@pytest.mark.parametrize('route',['/api/audits','/api/catalog','/api/employees','/api/tasks','/api/schedules','/api/system/backup','/api/system/photo','/inventory','/uploads/excels/a.xlsx','/docs','/index.html','/backend/.env'])
def test_employee_cannot_reach_management_or_legacy_routes(env,route):
    assert env['employee'].get(route).status_code==403

def test_manager_cannot_download_backup_or_escalate_accounts(env):
    assert env['manager'].get('/api/system/backup').status_code==403
    assert env['manager'].post('/api/team/people',json={'username':'evil','name':'Evil','role':'admin'}).status_code==403
    assert env['manager'].put('/api/team/people/1',json={'active':False,'role':'employee'}).status_code==403
    assert env['employee'].get('/api/team/people').status_code==403

def test_csrf_origin_and_revocation(env):
    http=env['employee'];csrf=http.headers.pop('X-CSRF-Token')
    assert http.post('/api/auth/logout').status_code==403
    http.headers['X-CSRF-Token']=csrf
    assert http.post('/api/auth/logout',headers={'Origin':'https://evil.invalid'}).status_code==403
    assert env['admin'].put('/api/team/people/'+str(env['uid']),json={'active':False,'role':'employee'}).status_code==200
    assert http.get('/api/auth/me').status_code==401

def test_invite_single_use_expiry_no_public_registration(env):
    res=env['manager'].post('/api/team/people',json={'username':'new.employee','name':'Nueva persona','role':'employee'});token=res.json()['activation_path'].split('#')[1]
    outsider=TestClient(env['app'])
    assert outsider.post('/api/team/people',json={'username':'bad','name':'Bad'}).status_code==401
    assert outsider.post('/api/auth/activate',json={'token':token,'password':'short'}).status_code==422
    assert outsider.post('/api/auth/activate',json={'token':token,'password':PASSWORD}).status_code==200
    assert outsider.post('/api/auth/activate',json={'token':token,'password':PASSWORD}).status_code==400
    renewed=env['admin'].post('/api/team/people/'+str(res.json()['id'])+'/invite').json()['activation_path'].split('#')[1]
    with ts.connection() as c:c.execute('UPDATE app_invites SET expires_at=0 WHERE token_hash=?',(ts.digest(renewed),))
    assert outsider.post('/api/auth/activate',json={'token':renewed,'password':PASSWORD}).status_code==400

def test_only_manager_decides_and_request_does_not_change_schedule(env):
    request={'date_from':week(),'date_to':week(),'kind':'restriction','day_off':True}
    r=env['employee'].post('/api/team/requests',json=request);assert r.status_code==200
    rid=r.json()['id'];assert r.json()['status']=='pending'
    assert env['admin'].post(f'/api/team/requests/{rid}/decision',json={'status':'approved'}).status_code==403
    assert env['employee'].post(f'/api/team/requests/{rid}/decision',json={'status':'approved'}).status_code==403
    assert env['manager'].post(f'/api/team/requests/{rid}/decision',json={'status':'approved'}).status_code==200
    assert env['employee'].get('/api/team/schedules/'+week()).json()['data'] is None
    assert env['other'].get('/api/team/requests').json()==[]

def test_draft_is_private_conflicts_block_publish_and_concurrency(env):
    lead=env['manager'];wk=week()
    body={'shifts':[{'employee_id':2,'day':0,'kind':'regular','start':'09:00','end':'17:00','pause':60}],'revision':0}
    r=lead.put('/api/team/schedules/'+wk,json=body);assert r.status_code==200,r.text
    assert lead.put('/api/team/schedules/'+wk,json=body).status_code==409
    assert env['employee'].get('/api/team/schedules/'+wk).json()['data'] is None
    assert env['employee'].put('/api/team/schedules/'+wk,json={**body,'revision':1}).status_code==403
    rid=env['employee'].post('/api/team/requests',json={'date_from':wk,'date_to':wk,'kind':'restriction','day_off':True}).json()['id']
    lead.post(f'/api/team/requests/{rid}/decision',json={'status':'approved'})
    assert lead.post(f'/api/team/schedules/{wk}/publish',json={'revision':1,'acknowledge_warnings':True}).status_code==409
    body['shifts'][0]['kind']='off';body['revision']=1
    assert lead.put('/api/team/schedules/'+wk,json=body).status_code==200
    assert lead.post(f'/api/team/schedules/{wk}/publish',json={'revision':2,'acknowledge_warnings':False}).status_code==409
    assert lead.post(f'/api/team/schedules/{wk}/publish',json={'revision':2,'acknowledge_warnings':True}).status_code==200
    published=env['employee'].get('/api/team/schedules/'+wk).json()['data']
    assert published['shifts'][0]['hours']==0
    body['revision']=2;body['notes']='Borrador secreto';lead.put('/api/team/schedules/'+wk,json=body)
    assert env['employee'].get('/api/team/schedules/'+wk).json()['data']['notes']!='Borrador secreto'

def test_suggestion_never_approves_requests_or_publishes(env):
    r=env['employee'].post('/api/team/requests',json={'date_from':week(),'date_to':week(),'note':'Prefiero apertura'})
    suggestion=env['manager'].post('/api/team/schedules/'+week()+'/suggest')
    assert suggestion.status_code==200,suggestion.text
    assert suggestion.json()['data']['shifts']
    assert env['employee'].get('/api/team/requests').json()[0]['status']=='pending'
    assert env['employee'].get('/api/team/schedules/'+week()).json()['data'] is None

def test_assignment_authorization_and_individual_progress(env):
    t=task(env,recipients=[env['uid'],env['other_uid']]);oid=t['occurrence_id']
    assert env['employee'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'doing'}).status_code==200
    assert env['employee'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'done'}).status_code==200
    listed=env['employee'].get('/api/team/agenda').json()['items'];row=next(t for t in listed if t['occurrence_id']==oid)
    assert row['done'] is False
    assert env['other'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'done'}).status_code==200
    row=next(t for t in env['employee'].get('/api/team/agenda').json()['items'] if t['occurrence_id']==oid)
    assert row['done'] is True
    assert env['employee'].delete('/api/team/agenda/'+str(t['id'])).status_code==403
    assert env['employee'].put('/api/team/agenda/'+str(t['id']),json={'title':'Changed','start_date':ts.today().isoformat()}).status_code==403

def test_unassigned_cannot_read_or_update_task_and_group_one(env):
    t=task(env,completion='one');oid=t['occurrence_id']
    assert all(x['occurrence_id']!=oid for x in env['other'].get('/api/team/agenda').json()['items'])
    assert env['other'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'done'}).status_code==404
    assert env['employee'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'done'}).status_code==200
    assert next(x for x in env['employee'].get('/api/team/agenda').json()['items'] if x['occurrence_id']==oid)['done']

def test_recurring_tasks_keep_future_pending_and_postpone_only_one(env):
    t=task(env,repeat_rule='daily');oid=t['occurrence_id']
    env['employee'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'done'})
    rows=[x for x in env['employee'].get('/api/team/agenda').json()['items'] if x['id']==t['id']]
    assert len(rows)>=15 and sum(x['done'] for x in rows)==1
    newdate=(ts.today()+timedelta(days=3)).isoformat()
    assert env['employee'].put(f'/api/team/occurrences/{oid}/postpone',json={'due_date':newdate}).status_code==403
    assert env['manager'].put(f'/api/team/occurrences/{oid}/postpone',json={'due_date':newdate}).status_code==200
    other=rows[1];again=env['employee'].get('/api/team/agenda').json()['items']
    assert next(x for x in again if x['occurrence_id']==other['occurrence_id'])['due_date']==other['due_date']

def test_checklist_notice_and_archive_undo(env):
    t=task(env,checklist=['Revisar','Registrar']);oid=t['occurrence_id']
    assert env['employee'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'done','checked':[0]}).status_code==422
    assert env['employee'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'blocked','note':''}).status_code==422
    assert env['employee'].put(f'/api/team/occurrences/{oid}/progress',json={'status':'done','checked':[0,1]}).status_code==200
    env['manager'].delete('/api/team/agenda/'+str(t['id']))
    assert all(x['id']!=t['id'] for x in env['employee'].get('/api/team/agenda').json()['items'])
    env['manager'].post('/api/team/agenda/'+str(t['id'])+'/restore')
    assert next(x for x in env['employee'].get('/api/team/agenda').json()['items'] if x['occurrence_id']==oid)['done']
    notice=task(env,kind='notice',completion='one')
    assert notice['completion']=='each'
    assert env['employee'].put('/api/team/occurrences/'+str(notice['occurrence_id'])+'/progress',json={'status':'doing'}).status_code==422

def test_migration_is_idempotent_and_backup_includes_new_tables(env):
    t=task(env)
    with ts.connection() as c:
        original=c.execute('SELECT COUNT(*) FROM store_tasks').fetchone()[0]
        count=c.execute('SELECT COUNT(*) FROM app_agenda').fetchone()[0]
    ts.initialize()
    with ts.connection() as c:
        assert c.execute('SELECT COUNT(*) FROM store_tasks').fetchone()[0]==original
        assert c.execute('SELECT COUNT(*) FROM app_agenda').fetchone()[0]==count
    r=env['admin'].get('/api/system/backup');assert r.status_code==200
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:(env['tmp']/'snapshot.db').write_bytes(z.read('backend/inventario.db'))
    conn=sqlite3.connect(env['tmp']/'snapshot.db')
    assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not conn.execute('PRAGMA foreign_key_check').fetchall()
    assert conn.execute('SELECT COUNT(*) FROM app_users').fetchone()[0]==4
    conn.close()

def test_task_photo_is_private_and_in_backup(env):
    from PIL import Image
    t=task(env);out=io.BytesIO();Image.new('RGB',(8,8),'green').save(out,format='PNG')
    endpoint=f"/api/team/agenda/{t['id']}/photo"
    assert env['employee'].post(endpoint,files={'file':('photo.png',out.getvalue(),'image/png')}).status_code==403
    assert env['manager'].post(endpoint,files={'file':('photo.png',out.getvalue(),'image/png')}).status_code==200
    photo=f"/api/team/occurrences/{t['occurrence_id']}/photo"
    assert env['employee'].get(photo).headers['content-type']=='image/jpeg'
    assert env['other'].get(photo).status_code==404
    with zipfile.ZipFile(io.BytesIO(env['admin'].get('/api/system/backup').content)) as archive:
        assert any(name.startswith('backend/uploads/agenda-assets/') for name in archive.namelist())

def test_password_change_revokes_sessions_and_old_invites(env):
    token=env['admin'].post(f"/api/team/people/{env['uid']}/invite").json()['activation_path'].split('#')[1]
    assert env['employee'].post('/api/auth/password',json={'current_password':PASSWORD,'password':'replacement-password-123'}).status_code==200
    assert env['employee'].get('/api/auth/me').status_code==401
    http=TestClient(env['app'])
    assert http.post('/api/auth/activate',json={'token':token,'password':PASSWORD}).status_code==400
    assert http.post('/api/auth/login',json={'username':'asesora','password':'replacement-password-123'}).status_code==200
    http.close()
