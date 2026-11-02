from datetime import date
from server.store import InvalidInput

def validate_dependencies(tasks):
    ids={};done=set();visiting=set()
    for task in tasks:
        ident=task.get('id')
        if ident is not None:
            if not isinstance(ident,str) or not 1<=len(ident)<=100 or ident in ids:raise InvalidInput('Identificador de tarefa inválido.')
            ids[ident]=task
        deps=task.get('dependsOn',[])
        if not isinstance(deps,list) or len(deps)>100 or any(not isinstance(d,str) for d in deps) or len(set(deps))!=len(deps):raise InvalidInput('Dependências inválidas.')
        for field in ['start','due']:
            if task.get(field):
                try:date.fromisoformat(task[field])
                except (ValueError,TypeError):raise InvalidInput('Data da tarefa inválida.') from None
        if task.get('start') and (not task.get('due') or task['start']>task['due']):raise InvalidInput('O prazo deve ser igual ou posterior ao início.')
    # Iterative traversal also handles long imported chains without recursive overflow.
    for task in tasks:
        stack=[(task,False)]
        while stack:
            current,leaving=stack.pop();ident=id(current)
            if leaving:visiting.discard(ident);done.add(ident);continue
            if ident in done:continue
            if ident in visiting:raise InvalidInput('As dependências criam um ciclo.')
            visiting.add(ident);stack.append((current,True))
            for parent_id in current.get('dependsOn',[]):
                parent=ids.get(parent_id)
                if parent is None:raise InvalidInput('A tarefa anterior não existe.')
                if current.get('status')!='A fazer' and parent['status']!='Concluído':raise InvalidInput('Conclua as tarefas anteriores antes de iniciar esta tarefa.')
                stack.append((parent,False))
    return True
