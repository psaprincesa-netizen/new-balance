"""Immediate form-to-project rules. Effects and execution records share one transaction."""
import json
import secrets
import time
from server.store import InvalidInput

PRIORITIES=('Baixa','Normal','Alta','Urgente')


def owner_form(workspace,db,user,form_id):
    row=workspace.accessible(db,user,form_id)
    if not row or row['deleted'] or row['kind']!='form':raise LookupError('Formulário não encontrado.')
    if row['owner']!=user:raise PermissionError('Somente o proprietário administra a automação.')
    return row


def settings(workspace,user,form_id,offset=0):
    with workspace.store.connect() as db:
        owner_form(workspace,db,user,form_id)
        row=db.execute('SELECT config FROM form_automations WHERE form_id=?',(form_id,)).fetchone()
        runs=[dict(r) for r in db.execute('''SELECT id, status, detail, created, updated, target_id, task_id, title, payload
            FROM automation_runs WHERE form_id=? ORDER BY created DESC,id DESC LIMIT 50 OFFSET ?''',(form_id,offset))]
        for run in runs:
            payload=json.loads(run.pop('payload'));run['retryable']=bool(payload.get('retryable'));run['approval']=payload.get('approval');run['priority']=payload.get('priority','Normal')
        return {'config':json.loads(row['config']) if row else None,'runs':runs,'next_offset':offset+50 if len(runs)==50 else None}


def configure(workspace,user,form_id,data):
    if type(data.get('requireApproval',False)) is not bool:raise InvalidInput('Estado de aprovação inválido.')
    if type(data.get('enabled')) is not bool:raise InvalidInput('Estado da automação inválido.')
    with workspace.store.connect() as db:
        workspace.store.begin_write(db,form_id)
        row=owner_form(workspace,db,user,form_id)
        from server.workspace import Conflict
        if type(data.get('version')) is not int or data['version']!=row['version']:raise Conflict('O formulário mudou. Atualize o painel antes de configurar a automação.')
        previous=db.execute('SELECT config FROM form_automations WHERE form_id=?',(form_id,)).fetchone()
        if not data['enabled']:
            config=json.loads(previous['config']) if previous else {'enabled':False}
            config['enabled']=False
        else:
            target_id=data.get('targetId')
            if not isinstance(target_id,str) or not 1<=len(target_id)<=100:raise InvalidInput('Escolha um projeto próprio.')
            target=db.execute('SELECT owner, kind, deleted FROM items WHERE id=?',(target_id,)).fetchone()
            if not target or target['owner']!=user or target['kind']!='board' or target['deleted']:raise InvalidInput('O destino precisa ser um projeto ativo do mesmo proprietário.')
            content=json.loads(row['content']);fields=content.get('fields') or [{'type':'text'} for _ in content['questions']]
            config={'enabled':True,'targetId':target_id,'requireApproval':data.get('requireApproval',False)}
            for key in ('titleQuestion','whenQuestion'):
                index=data.get(key)
                if index is not None and (type(index) is not int or not 0<=index<len(content['questions'])):raise InvalidInput('Pergunta de origem inválida.')
                if index is not None and content['questions'].count(content['questions'][index])!=1:raise InvalidInput('As perguntas usadas na automação precisam ter títulos únicos.')
                config[key]=index;config[key+'Name']=content['questions'][index] if index is not None else None
            prefix=data.get('prefix','Nova resposta: ');priority=data.get('priority','Normal')
            if not isinstance(prefix,str) or len(prefix)>100 or priority not in PRIORITIES:raise InvalidInput('Título ou prioridade inválidos.')
            config.update(prefix=prefix,priority=priority)
            if config['whenQuestion'] is not None:
                i=config['whenQuestion'];value=data.get('whenValue')
                if fields[i].get('type')!='choice' or not isinstance(value,str) or not value or value not in fields[i].get('options',[]):raise InvalidInput('A condição exige uma opção de pergunta de escolha única.')
                config['whenValue']=value
        db.execute('INSERT INTO form_automations (form_id, config) VALUES (?,?) ON CONFLICT(form_id) DO UPDATE SET config=excluded.config',(form_id,json.dumps(config)))
        return {'config':config}


def execute_run(workspace,db,source,run):
    if run['status'] in ('completed','skipped','awaiting_approval','rejected'):return
    payload=json.loads(run['payload']);target_id=run['target_id'];now=time.time_ns()//1000000
    workspace.store.begin_write(db,target_id)
    target=db.execute('SELECT * FROM items WHERE id=?',(target_id,)).fetchone()
    detail='';status='failed'
    if not target or target['owner']!=source['owner'] or target['kind']!='board' or target['deleted']:
        detail='Projeto de destino indisponível. Restaure-o ou revise o destino.'
    else:
        content=json.loads(target['content']);tasks=content.get('tasks',[])
        if any(t.get('id')==run['task_id'] for t in tasks):status='completed';detail='Tarefa já registrada.'
        elif len(tasks)>=1000:detail='O projeto atingiu o limite de 1000 tarefas. Libere espaço antes de reprocessar.'
        else:
            task={'id':run['task_id'],'title':run['title'],'status':'A fazer','due':'','priority':payload['priority'],'assignee':'','depends':[],'subtasks':[]}
            content['tasks']=[*tasks,task]
            try:
                from server.schema import validate_content
                validate_content('board',content)
                _,encoded=workspace.validate({'title':target['title'],'content':content})
            except InvalidInput:
                detail='O conteúdo do projeto excede um limite ou precisa ser revisado antes de reprocessar.'
            else:
                version=target['version']+1
                db.execute('UPDATE items SET content=?,version=?,updated=? WHERE id=?',(encoded,version,now,target_id))
                db.execute('INSERT INTO versions VALUES (?,?,?,?,?)',(target_id,version,target['title'],encoded,now))
                status='completed';detail='Tarefa criada no projeto.'
    db.execute('UPDATE automation_runs SET status=?,detail=?,updated=? WHERE id=?',(status,detail,now,run['id']))


def on_public_response(workspace,db,source,content,response):
    setting=db.execute('SELECT config FROM form_automations WHERE form_id=?',(source['id'],)).fetchone()
    if not setting:return
    config=json.loads(setting['config'])
    if not config.get('enabled'):return
    now=time.time_ns()//1000000;ident=secrets.token_hex(16);status='pending';detail=''
    for key in ('titleQuestion','whenQuestion'):
        index=config.get(key)
        if index is not None and (index>=len(content['questions']) or content['questions'][index]!=config.get(key+'Name') or content['questions'].count(config.get(key+'Name'))!=1):
            status='failed';detail='As perguntas mudaram. Revise a automação para novas respostas; esta execução não pode ser reprocessada.'
    index=config.get('titleQuestion');answer=response['answers'][index] if index is not None and index<len(response['answers']) else ''
    title=(config.get('prefix','')+(answer or source['title'])).strip()[:200] or 'Nova resposta de formulário'
    when=config.get('whenQuestion')
    if status=='pending' and when is not None:
        fields=content.get('fields') or [{'type':'text'} for _ in content['questions']]
        if fields[when].get('type')!='choice' or config.get('whenValue') not in fields[when].get('options',[]):
            status='failed';detail='A opção usada pela condição mudou. Revise a automação para novas respostas.'
    if status=='pending' and config.get('whenQuestion') is not None and response['answers'][config['whenQuestion']]!=config['whenValue']:
        status='skipped';detail='Condição não atendida.'
    payload={'priority':config.get('priority','Normal'),'retryable':status=='pending'}
    if status=='pending' and config.get('requireApproval'):
        status='awaiting_approval';detail='Aguardando decisão do proprietário antes de criar a tarefa.'
        payload['approval']={'decision':None}
        payload['review']={'questions':response['questions'],'answers':response['answers'],'at':response['at']}
    db.execute('''INSERT INTO automation_runs (id, form_id, response_id, target_id, task_id, title, payload, status, detail, created, updated)
        VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(form_id,response_id) DO NOTHING''',
        (ident,source['id'],response['id'],config['targetId'],'form-'+response['id'],title,json.dumps(payload),status,detail,now,now))
    run=db.execute('SELECT * FROM automation_runs WHERE form_id=? AND response_id=?',(source['id'],response['id'])).fetchone()
    if run['status']=='pending':execute_run(workspace,db,source,run)


def retry(workspace,user,form_id,run_id):
    if not isinstance(run_id,str) or not 1<=len(run_id)<=100:raise InvalidInput('Identificador de execução inválido.')
    with workspace.store.connect() as db:
        workspace.store.begin_write(db,form_id);source=owner_form(workspace,db,user,form_id)
        run=db.execute('SELECT * FROM automation_runs WHERE id=? AND form_id=?',(run_id,form_id)).fetchone()
        if not run:raise LookupError('Execução não encontrada.')
        if run['status'] in ('awaiting_approval','rejected'):raise InvalidInput('Esta execução precisa de uma aprovação pendente; uma rejeição é definitiva.')
        if run['status']=='failed' and not json.loads(run['payload']).get('retryable'):raise InvalidInput('Esta execução tem uma configuração antiga inválida. Revise a regra para os próximos envios.')
        execute_run(workspace,db,source,run)
        return {'ok':True}


def decide(workspace,user,form_id,run_id,decision):
    """One immutable owner decision and its task effect commit atomically."""
    from server.workspace import Conflict
    if not isinstance(run_id,str) or not 1<=len(run_id)<=100 or decision not in ('approve','reject'):
        raise InvalidInput('Decisão ou execução inválida.')
    with workspace.store.connect() as db:
        workspace.store.begin_write(db,form_id)
        source=owner_form(workspace,db,user,form_id)
        run=db.execute('SELECT * FROM automation_runs WHERE id=? AND form_id=?',(run_id,form_id)).fetchone()
        if not run:raise LookupError('Execução não encontrada.')
        payload=json.loads(run['payload']);approval=payload.get('approval')
        if run['status']!='awaiting_approval':
            if approval and approval.get('decision')==decision:return {'ok':True}
            raise Conflict('Esta execução não aguarda essa decisão. Atualize o painel.')
        now=time.time_ns()//1000000
        payload['approval']={'decision':decision,'actor':user,'at':now}
        rejected=decision=='reject'
        if rejected:payload['retryable']=False
        db.execute('UPDATE automation_runs SET payload=?,status=?,detail=?,updated=? WHERE id=?',
            (json.dumps(payload),'rejected' if rejected else 'pending',
             'Solicitação rejeitada pelo proprietário.' if rejected else 'Solicitação aprovada pelo proprietário.',now,run_id))
        if not rejected:
            run=db.execute('SELECT * FROM automation_runs WHERE id=? AND form_id=?',(run_id,form_id)).fetchone()
            execute_run(workspace,db,source,run)
    return {'ok':True}


def review(workspace,user,form_id,run_id):
    if not isinstance(run_id,str) or not 1<=len(run_id)<=100:raise InvalidInput('Identificador de execução inválido.')
    with workspace.store.connect() as db:
        owner_form(workspace,db,user,form_id)
        row=db.execute('SELECT payload FROM automation_runs WHERE id=? AND form_id=?',(run_id,form_id)).fetchone()
        snapshot=json.loads(row['payload']).get('review') if row else None
        if not snapshot:raise LookupError('Resposta original indisponível para esta execução.')
        return snapshot
