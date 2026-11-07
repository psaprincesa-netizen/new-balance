"""Explicit read-only exact joins between separately authorized table files."""
def valid_relations(content):
    relations=content.get('relations',[])
    if not isinstance(relations,list) or len(relations)>10:return False
    ids=set()
    for r in relations:
        if not isinstance(r,dict):return False
        ident=r.get('id');source=r.get('sourceColumn');target=r.get('targetColumn')
        if not isinstance(ident,str) or not 1<=len(ident)<=100 or ident in ids:return False
        ids.add(ident)
        if not isinstance(r.get('name'),str) or not 1<=len(r['name'].strip())<=200:return False
        if not isinstance(r.get('targetId'),str) or not 1<=len(r['targetId'])<=100:return False
        if type(source) is not int or not 0<=source<len(content['columns']):return False
        if type(target) is not int or not 0<=target<26:return False
        if not content['columns'][source].strip() or r.get('sourceName')!=content['columns'][source] or content['columns'].count(r.get('sourceName'))!=1:return False
        if not isinstance(r.get('targetName'),str) or not r['targetName'].strip() or len(r['targetName'])>4000:return False
    return True


def related_records(workspace,user,item_id,relation_id,row_index,version,offset=0):
    import json
    from server.store import InvalidInput
    from server.workspace import Conflict
    if type(row_index) is not int or type(version) is not int or type(offset) is not int or offset<0:
        raise InvalidInput('Consulta de relacionamento inválida.')
    with workspace.store.connect() as db:
        source=workspace.accessible(db,user,item_id)
        if not source or source['deleted'] or source['kind']!='table':raise LookupError('Tabela não encontrada.')
        if source['version']!=version:raise Conflict('A tabela mudou. Reabra a versão atual antes de consultar.')
        content=json.loads(source['content'])
        relation=next((r for r in content.get('relations',[]) if r['id']==relation_id),None)
        if relation is None:raise LookupError('Relacionamento não encontrado.')
        if not 0<=row_index<len(content['rows']):raise InvalidInput('Registro de origem inválido.')
        target=workspace.accessible(db,user,relation['targetId'])
        if not target or target['deleted'] or target['kind']!='table':raise LookupError('Tabela vinculada indisponível ou sem acesso.')
        data=json.loads(target['content']);column=relation['targetColumn']
        if column>=len(data['columns']) or data['columns'][column]!=relation['targetName'] or data['columns'].count(relation['targetName'])!=1:
            raise Conflict('O campo da tabela vinculada mudou. Remova e recrie o relacionamento antes de consultar.')
        key=content['rows'][row_index][relation['sourceColumn']]
        matches=[row for row in data['rows'] if key!='' and row[column]==key]
        return {'title':target['title'],'columns':data['columns'],'rows':matches[offset:offset+50],
                'total':len(matches),'next_offset':offset+50 if offset+50<len(matches) else None,
                'sourceVersion':source['version'],'targetVersion':target['version']}
