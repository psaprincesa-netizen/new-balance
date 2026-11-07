from datetime import date
from server.store import InvalidInput

def validate_dependencies(tasks):
    ids={};done=set();visiting=set()
    for task in tasks:
        ident=task.get('id')
        if ident is not None:
            if not isinstance(ident,str) or not 1<=len(ident)<=100 or ident in ids:raise InvalidInput('Identificador de tarefa inválido.')
            ids[ident]=task
        deps=task.get('depends',task.get('dependsOn',[]))
        if not isinstance(deps,list) or len(deps)>100 or any(not isinstance(d,str) for d in deps) or len(set(deps))!=len(deps):raise InvalidInput('Dependências inválidas.')
        for field in ['start','due']:
            if task.get(field):
                if field=='due' and not task.get('start') and not __import__('re').fullmatch(r'\d{4}-\d{2}-\d{2}',str(task[field])):continue
                try:date.fromisoformat(task[field])
                except (ValueError,TypeError):raise InvalidInput('Data da tarefa inválida.') from None
        if task.get('start') and task.get('due') and task['start']>task['due'] and not task.get('milestone'):raise InvalidInput('O prazo deve ser igual ou posterior ao início.')
    # Iterative traversal also handles long imported chains without recursive overflow.
    for task in tasks:
        stack=[(task,False)]
        while stack:
            current,leaving=stack.pop();ident=id(current)
            if leaving:visiting.discard(ident);done.add(ident);continue
            if ident in done:continue
            if ident in visiting:raise InvalidInput('As dependências criam um ciclo.')
            visiting.add(ident);stack.append((current,True))
            for parent_id in current.get('depends',current.get('dependsOn',[])):
                parent=ids.get(parent_id)
                if parent is None:raise InvalidInput('A tarefa anterior não existe.')
                if current.get('status')!='A fazer' and parent['status']!='Concluído':raise InvalidInput('Conclua as tarefas anteriores antes de iniciar esta tarefa.')
                stack.append((parent,False))
    return True


def valid_planning(content):
    """Bound snapshots and capacity profiles without trusting client totals."""
    import math
    from datetime import datetime
    resources = content.get('resources', [])
    if not isinstance(resources, list) or len(resources) > 200:
        return False
    names = set()
    for resource in resources:
        if not isinstance(resource, dict):return False
        name, hours = resource.get('name'), resource.get('dailyHours')
        if not isinstance(name, str) or not name.strip() or name != name.strip() or len(name) > 100 or name in names:return False
        if type(hours) not in (int, float) or not math.isfinite(hours) or not 0 <= hours <= 24:return False
        names.add(name)
    baseline = content.get('baseline')
    if baseline is None:return True
    if not isinstance(baseline, dict):return False
    try:
        if not isinstance(baseline.get('capturedAt'),str) or len(baseline['capturedAt']) > 40:return False
        datetime.fromisoformat(baseline['capturedAt'].replace('Z','+00:00'))
    except (ValueError, TypeError):return False
    tasks = baseline.get('tasks')
    if not isinstance(tasks, list) or len(tasks) > 1000:return False
    ids = set()
    for task in tasks:
        if not isinstance(task,dict):return False
        ident = task.get('id')
        if not isinstance(ident,str) or not 1 <= len(ident) <= 100 or ident in ids:return False
        ids.add(ident)
        if not isinstance(task.get('title'),str) or not 1 <= len(task['title']) <= 200:return False
        for key in ('plannedHours','hourlyRate','fixedCost'):
            value = task.get(key)
            if type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value <= 100_000:return False
        for key in ('start','due'):
            value = task.get(key)
            if not isinstance(value,str):return False
            if value:
                try:date.fromisoformat(value)
                except ValueError:return False
        if bool(task['start']) != bool(task['due']) or task['start'] > task['due']:return False
    return True
