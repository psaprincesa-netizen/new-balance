"""Date-based recurring project tasks, driven by a bounded authenticated daily cron."""
import calendar,json,secrets,time,re,os
from datetime import date,datetime,timedelta,timezone
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from server.store import InvalidInput
from server.workspace import Conflict

CADENCES=('once','daily','weekly','monthly')
def today(zone,now=None):return (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(zone)).date()
def parse_day(value):
    try:
        if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError()
        return date.fromisoformat(value)
    except (ValueError,TypeError):raise InvalidInput('Data inválida; use AAAA-MM-DD.') from None

def next_day(current,config):
    day=parse_day(current);cadence=config['cadence']
    if cadence=='once':return None
    if cadence=='daily':return (day+timedelta(days=1)).isoformat()
    if cadence=='weekly':return (day+timedelta(days=7)).isoformat()
    year=day.year+(day.month==12);month=1 if day.month==12 else day.month+1
    anchor=parse_day(config['firstDate']).day
    return date(year,month,min(anchor,calendar.monthrange(year,month)[1])).isoformat()

def owned(db,user,ident):
    row=db.execute('SELECT * FROM schedules WHERE id=? AND user_id=?',(ident,user)).fetchone()
    if not row:raise LookupError('Agendamento não encontrado.')
    return row

def validate(workspace,db,user,config,now=None,check_target=True):
    if not isinstance(config,dict) or set(config)!={'name','targetId','taskTitle','priority','cadence','firstDate','timezone','dueOffset'}:raise InvalidInput('Configuração de agendamento inválida.')
    for key,limit in [('name',100),('taskTitle',200),('targetId',100),('timezone',100)]:
        if not isinstance(config[key],str) or not config[key].strip() or len(config[key])>limit:raise InvalidInput('Preencha nome, título, projeto e fuso.')
    if config['priority'] not in ('Baixa','Normal','Alta','Urgente') or config['cadence'] not in CADENCES:raise InvalidInput('Prioridade ou repetição inválida.')
    if type(config['dueOffset']) is not int or not 0<=config['dueOffset']<=365:raise InvalidInput('O prazo deve ser de 0 a 365 dias após a ocorrência.')
    try:today(config['timezone'],now)
    except (ZoneInfoNotFoundError,ValueError):raise InvalidInput('Fuso horário inválido.') from None
    first=parse_day(config['firstDate'])
    if not 2020<=first.year<=2098:raise InvalidInput('A data deve estar entre 2020 e 2098.')
    target=db.execute('SELECT owner,kind,deleted FROM items WHERE id=?',(config['targetId'],)).fetchone()
    if check_target and (not target or target['owner']!=user or target['kind']!='board' or target['deleted']):raise InvalidInput('Escolha um projeto ativo do mesmo proprietário.')
    return config

def listing(workspace,user,deleted=False,offset=0):
    with workspace.store.connect() as db:
        rows=[dict(r)|{'config':json.loads(r['config'])} for r in db.execute('SELECT * FROM schedules WHERE user_id=? AND deleted=? ORDER BY updated DESC,id LIMIT 50 OFFSET ?',(user,int(deleted),offset))]
        return {'items':rows,'next_offset':offset+50 if len(rows)==50 else None,'automatic_configured':bool(os.environ.get('VERCEL') and os.environ.get('CRON_SECRET'))}

def save(workspace,user,data,ident=None,now=None):
    if type(data.get('active')) is not bool or type(data.get('version')) is not int:raise InvalidInput('Estado ou versão inválidos.')
    config=data.get('config');stamp=time.time_ns()//1000000
    with workspace.store.connect() as db:
        # Per-account limits and per-rule execution use the same lock order.
        workspace.store.begin_write(db,'schedules-user:'+user)
        if ident:workspace.store.begin_write(db,'schedule:'+ident)
        previous=owned(db,user,ident) if ident else None
        if previous and previous['deleted']:raise InvalidInput('Restaure o agendamento antes de editá-lo.')
        if data['version']!=(previous['version'] if previous else 0):raise Conflict('O agendamento mudou. Atualize antes de salvar.')
        old=json.loads(previous['config']) if previous else None
        unchanged_target=bool(old and isinstance(config,dict) and config.get('targetId')==old.get('targetId'))
        validate(workspace,db,user,config,now,check_target=data['active'] or not unchanged_target)
        structural=not old or any(config[k]!=old[k] for k in ('firstDate','cadence','timezone'))
        if structural and parse_day(config['firstDate'])<today(config['timezone'],now):raise InvalidInput('Uma nova agenda precisa começar hoje ou em uma data futura.')
        due=config['firstDate'] if structural else previous['next_due']
        if data['active'] and due is None:raise InvalidInput('Escolha uma nova data para reativar uma agenda concluída.')
        if not previous:
            if db.execute('SELECT COUNT(*) AS n FROM schedules WHERE user_id=? AND deleted=0',(user,)).fetchone()['n']>=50:raise InvalidInput('Limite de 50 agendamentos; exclua um antes de criar outro.')
            ident=secrets.token_hex(16)
            db.execute('INSERT INTO schedules(id,user_id,config,active,deleted,next_due,version,updated) VALUES (?,?,?,?,0,?,1,?)',(ident,user,json.dumps(config),int(data['active']),due,stamp))
        else:db.execute('UPDATE schedules SET config=?,active=?,next_due=?,version=version+1,updated=? WHERE id=?',(json.dumps(config),int(data['active']),due,stamp,ident))
    return {'id':ident}

def trash(workspace,user,ident,deleted,version):
    if type(deleted) is not bool or type(version) is not int:raise InvalidInput('Estado ou versão inválidos.')
    with workspace.store.connect() as db:
        workspace.store.begin_write(db,'schedules-user:'+user);workspace.store.begin_write(db,'schedule:'+ident)
        row=owned(db,user,ident)
        if row['version']!=version:raise Conflict('O agendamento mudou. Atualize o painel.')
        if not deleted and row['deleted'] and db.execute('SELECT COUNT(*) AS n FROM schedules WHERE user_id=? AND deleted=0',(user,)).fetchone()['n']>=50:raise InvalidInput('Limite de 50 agendamentos ativos na biblioteca.')
        db.execute('UPDATE schedules SET deleted=?,active=0,version=version+1,updated=? WHERE id=?',(int(deleted),time.time_ns()//1000000,ident))
    return {'ok':True}

def history(workspace,user,ident,offset=0):
    with workspace.store.connect() as db:
        owned(db,user,ident)
        rows=[dict(r) for r in db.execute('SELECT id,due_date,status,detail,created,updated,payload FROM schedule_runs WHERE schedule_id=? ORDER BY due_date DESC,id DESC LIMIT 50 OFFSET ?',(ident,offset))]
        for row in rows:
            payload=json.loads(row.pop('payload'));row.update(title=payload['title'],targetId=payload['targetId'],taskDue=payload['due'])
        return {'items':rows,'next_offset':offset+50 if len(rows)==50 else None,'automatic_configured':bool(os.environ.get('VERCEL') and os.environ.get('CRON_SECRET'))}

def effect(workspace,db,rule,run):
    if run['status']=='completed':return
    payload=json.loads(run['payload']);target_id=payload['targetId'];workspace.store.begin_write(db,target_id)
    target=db.execute('SELECT * FROM items WHERE id=?',(target_id,)).fetchone();status='failed';detail='Projeto de destino indisponível. Restaure-o antes de reprocessar.';stamp=time.time_ns()//1000000
    if target and target['owner']==rule['user_id'] and target['kind']=='board' and not target['deleted']:
        content=json.loads(target['content']);tasks=content.get('tasks',[]);task_id='schedule-'+run['id']
        if any(t.get('id')==task_id for t in tasks):status='completed';detail='Tarefa já registrada.'
        elif len(tasks)>=1000:detail='O projeto atingiu o limite de 1000 tarefas. Libere espaço e reprocesse.'
        else:
            content['tasks']=[*tasks,{'id':task_id,'title':payload['title'],'status':'A fazer','due':payload['due'],'priority':payload['priority'],'assignee':'','depends':[],'subtasks':[]}]
            try:
                from server.schema import validate_content
                validate_content('board',content);_,encoded=workspace.validate({'title':target['title'],'content':content})
            except InvalidInput:detail='O projeto excede um limite ou precisa ser revisado antes de reprocessar.'
            else:
                version=target['version']+1
                db.execute('UPDATE items SET content=?,version=?,updated=? WHERE id=?',(encoded,version,stamp,target_id))
                db.execute('INSERT INTO versions VALUES (?,?,?,?,?)',(target_id,version,target['title'],encoded,stamp))
                status='completed';detail='Tarefa criada no projeto.'
    db.execute('UPDATE schedule_runs SET status=?,detail=?,updated=? WHERE id=?',(status,detail,stamp,run['id']))

def process_rule(workspace,ident,user=None,now=None,limit=5,deadline=None):
    processed=0
    # Each occurrence has its own short transaction; interruption resumes from next_due.
    for _ in range(limit):
        if deadline is not None and time.monotonic()>=deadline:break
        with workspace.store.connect() as db:
            workspace.store.begin_write(db,'schedule:'+ident)
            row=db.execute('SELECT * FROM schedules WHERE id=?',(ident,)).fetchone()
            if not row or (user and row['user_id']!=user):raise LookupError('Agendamento não encontrado.')
            if row['deleted'] or not row['active'] or not row['next_due']:break
            config=json.loads(row['config']);due=row['next_due']
            if parse_day(due)>today(config['timezone'],now):break
            run=db.execute('SELECT * FROM schedule_runs WHERE schedule_id=? AND due_date=?',(ident,due)).fetchone()
            if not run:
                stamp=time.time_ns()//1000000;run_id=secrets.token_hex(16)
                payload={'title':config['taskTitle'],'priority':config['priority'],'targetId':config['targetId'],'due':(parse_day(due)+timedelta(days=config['dueOffset'])).isoformat()}
                db.execute('INSERT INTO schedule_runs(id,schedule_id,due_date,payload,status,detail,created,updated) VALUES (?,?,?,?,?,?,?,?)',(run_id,ident,due,json.dumps(payload),'pending','',stamp,stamp))
                run=db.execute('SELECT * FROM schedule_runs WHERE id=?',(run_id,)).fetchone()
                effect(workspace,db,row,run)
            following=next_day(due,config)
            if following and parse_day(following).year>2099:following=None
            db.execute('UPDATE schedules SET next_due=?,active=?,version=version+1,updated=? WHERE id=?',(following,int(bool(following)),time.time_ns()//1000000,ident))
            processed+=1
    return {'processed':processed}

def process_due(workspace,user=None,now=None,limit=20,max_seconds=None):
    # UTC + 1 day bounds all IANA local dates without scanning every active rule.
    cutoff=((now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()+timedelta(days=1)).isoformat()
    with workspace.store.connect() as db:
        rows=db.execute('SELECT id FROM schedules WHERE active=1 AND deleted=0 AND next_due<=?'+(' AND user_id=?' if user else '')+' ORDER BY next_due,id LIMIT ?',(cutoff,user,limit) if user else (cutoff,limit)).fetchall()
    budget=limit;total=0;deadline=time.monotonic()+max_seconds if max_seconds is not None else None
    for row in rows:
        result=process_rule(workspace,row['id'],user,now,limit=min(5,budget),deadline=deadline);total+=result['processed'];budget-=result['processed']
        if budget<=0 or (deadline is not None and time.monotonic()>=deadline):break
    return {'processed':total}

def retry(workspace,user,ident,run_id):
    if not isinstance(run_id,str) or not 1<=len(run_id)<=100:raise InvalidInput('Execução inválida.')
    with workspace.store.connect() as db:
        workspace.store.begin_write(db,'schedule:'+ident);rule=owned(db,user,ident)
        if rule['deleted']:raise InvalidInput('Restaure o agendamento antes de reprocessar.')
        run=db.execute('SELECT * FROM schedule_runs WHERE id=? AND schedule_id=?',(run_id,ident)).fetchone()
        if not run:raise LookupError('Execução não encontrada.')
        effect(workspace,db,rule,run)
    return {'ok':True}
