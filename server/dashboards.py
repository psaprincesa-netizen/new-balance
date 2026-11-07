"""Private dashboards: bounded live aggregates, checked against current source access."""
import json, math, re, time
from decimal import Decimal, InvalidOperation
from server.store import InvalidInput
from server.workspace import Conflict

OPERATIONS=('count','sum','average','min','max')
BOARD_FIELDS=['Título','Estado','Prioridade','Responsável','Prazo']

def dataset(row):
    content=json.loads(row['content'])
    if row['kind']=='table':return content['columns'],content['rows']
    if row['kind']=='board':
        return BOARD_FIELDS,[[str(t.get(k,'') or '') for k in ('title','status','priority','assignee','due')] for t in content['tasks']]
    raise InvalidInput('Use uma tabela ou um projeto como fonte.')

def source(workspace,db,user,ident):
    row=workspace.accessible(db,user,ident)
    if not row or row['deleted']:raise LookupError('Fonte indisponível ou sem acesso.')
    dataset(row)
    return row

def sources(workspace,user):
    from server.database import PostgresConnection
    with workspace.store.connect() as db:
        # Fetch only field definitions, never hundreds of full source datasets.
        columns_sql="i.content::jsonb -> 'columns'" if isinstance(db,PostgresConnection) else "json_extract(i.content,'$.columns')"
        rows=db.execute(f'''SELECT DISTINCT i.id,i.title,i.kind,i.version,
          CASE WHEN i.kind='table' THEN {columns_sql} ELSE NULL END AS columns
          FROM items i LEFT JOIN shares s ON s.item_id=i.id AND s.user_id=?
          WHERE i.deleted=0 AND i.kind IN ('table','board') AND (i.owner=? OR s.user_id=?) ORDER BY i.title,i.id LIMIT 501''',(user,user,user)).fetchall()
        items=[]
        for row in rows[:500]:
            item=dict(row)
            item['columns']=BOARD_FIELDS if item['kind']=='board' else json.loads(item['columns']) if isinstance(item['columns'],str) else item['columns']
            items.append(item)
        return {'items':items,'limited':len(rows)>500}

def check_field(field,columns):
    if (not isinstance(field,dict) or set(field)!={'index','name'} or type(field['index']) is not int
        or not 0<=field['index']<len(columns) or columns[field['index']]!=field['name'] or columns.count(field['name'])!=1):
        raise InvalidInput('Campo alterado ou ambíguo. Edite o indicador e escolha novamente os campos.')
    return field['index']

def validate_widget(workspace,db,user,widget):
    if not isinstance(widget,dict) or set(widget)-{'id','title','sourceId','operation','valueField','groupField','filter'}:raise InvalidInput('Indicador inválido.')
    for key,limit in [('id',80),('title',100),('sourceId',100)]:
        if not isinstance(widget.get(key),str) or not widget[key].strip() or len(widget[key])>limit:raise InvalidInput('Nome, identificador ou fonte inválidos.')
    if widget.get('operation') not in OPERATIONS:raise InvalidInput('Operação inválida.')
    row=source(workspace,db,user,widget['sourceId']);columns,_=dataset(row)
    if widget['operation']!='count':check_field(widget.get('valueField'),columns)
    elif widget.get('valueField') is not None:raise InvalidInput('Contagem usa o número de registros.')
    if widget.get('groupField') is not None:check_field(widget['groupField'],columns)
    condition=widget.get('filter')
    if condition is not None:
        if not isinstance(condition,dict) or set(condition)!={'field','value'} or not isinstance(condition['value'],str) or len(condition['value'])>500:raise InvalidInput('Filtro inválido.')
        check_field(condition['field'],columns)
    return widget

def numeric(value):
    value=value.strip()
    if not value:return None
    # Canonical numeric text matches the typed table format. No ambiguous locale guessing.
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?',value) or len(value)>100:raise InvalidInput('A medida contém texto não numérico. Use ponto decimal, sem moeda ou separador de milhar.')
    try:number=Decimal(value)
    except InvalidOperation:raise InvalidInput('Número inválido.')
    if not number.is_finite() or abs(number)>Decimal('1e100'):raise InvalidInput('Número excede o limite do painel.')
    return number

def aggregate(rows,operation,index):
    if operation=='count':return len(rows)
    values=[numeric(r[index]) for r in rows];values=[v for v in values if v is not None]
    if not values:return None
    if operation=='sum':result=sum(values,Decimal(0))
    elif operation=='average':result=sum(values,Decimal(0))/len(values)
    elif operation=='min':result=min(values)
    else:result=max(values)
    number=float(result)
    if not math.isfinite(number) or (result!=0 and number==0):raise InvalidInput('Resultado excede o limite numérico.')
    return number

def evaluate(workspace,db,user,widget):
    validate_widget(workspace,db,user,widget)
    row=source(workspace,db,user,widget['sourceId']);columns,rows=dataset(row)
    condition=widget.get('filter')
    if condition:
        index=check_field(condition['field'],columns);rows=[r for r in rows if r[index]==condition['value']]
    index=check_field(widget['valueField'],columns) if widget['operation']!='count' else None
    result={'id':widget['id'],'sourceTitle':row['title'],'sourceVersion':row['version'],'rows':len(rows)}
    if widget.get('groupField') is not None:
        group_index=check_field(widget['groupField'],columns);groups={}
        for r in rows:
            groups.setdefault(r[group_index],[]).append(r)
            if len(groups)>50:raise InvalidInput('Mais de 50 categorias. Aplique um filtro ou escolha outro agrupamento.')
        result['groups']=[{'label':label,'value':aggregate(values,widget['operation'],index)} for label,values in sorted(groups.items())]
    else:result['value']=aggregate(rows,widget['operation'],index)
    return result

def get(workspace,user):
    with workspace.store.connect() as db:
        row=db.execute('SELECT * FROM dashboards WHERE user_id=?',(user,)).fetchone()
        config=json.loads(row['config']) if row else {'title':'Meu painel','widgets':[]}
        results=[]
        for widget in config['widgets']:
            try:results.append(evaluate(workspace,db,user,widget))
            except (InvalidInput,LookupError,PermissionError) as error:results.append({'id':widget['id'],'error':str(error)})
        return {'config':config,'version':row['version'] if row else 0,'results':results,'updated':time.time_ns()//1000000}

def save(workspace,user,data):
    config=data.get('config');expected=data.get('version')
    if (type(expected) is not int or expected<0 or not isinstance(config,dict) or set(config)!={'title','widgets'}
        or not isinstance(config['title'],str) or not config['title'].strip() or len(config['title'])>100
        or not isinstance(config['widgets'],list) or len(config['widgets'])>12):raise InvalidInput('Painel inválido: use um nome e até 12 indicadores.')
    with workspace.store.connect() as db:
        workspace.store.begin_write(db,'dashboard:'+user)
        row=db.execute('SELECT version FROM dashboards WHERE user_id=?',(user,)).fetchone()
        if expected!=(row['version'] if row else 0):raise Conflict('O painel mudou em outra aba. Atualize antes de salvar.')
        ids=set()
        for widget in config['widgets']:
            validate_widget(workspace,db,user,widget)
            if widget['id'] in ids:raise InvalidInput('Indicadores duplicados.')
            ids.add(widget['id'])
        db.execute('''INSERT INTO dashboards(user_id,config,version) VALUES (?,?,?)
          ON CONFLICT(user_id) DO UPDATE SET config=excluded.config,version=excluded.version''',(user,json.dumps(config),expected+1))
    return {'version':expected+1}
