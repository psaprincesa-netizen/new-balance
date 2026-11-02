import json,re
from server.store import InvalidInput

def bounds(address):
    match=re.fullmatch(r'([A-Z]{1,3})([1-9]\d{0,5})(?::([A-Z]{1,3})([1-9]\d{0,5}))?',str(address))
    if not match:raise InvalidInput('Intervalo protegido inválido.')
    a,b,c,d=match.groups();c=c or a;d=d or b
    def col(value):
        n=0
        for letter in value:n=n*26+ord(letter)-64
        return n-1
    x1,y1,x2,y2=col(a),int(b)-1,col(c),int(d)-1
    if x1>x2 or y1>y2 or x2>=1024 or y2>=100000 or (x2-x1+1)*(y2-y1+1)>50000:raise InvalidInput('Proteja até 50 mil células por intervalo.')
    return x1,y1,x2,y2

def valid_protection(content):
    ranges=content.get('protectedRanges',[])
    if not isinstance(ranges,list) or len(ranges)>20:return False
    for entry in ranges:
        if not isinstance(entry,dict) or not isinstance(entry.get('sheetId'),str) or len(entry['sheetId'])>100:return False
        if not isinstance(entry.get('name',''),str) or len(entry.get('name',''))>100:return False
        try:bounds(entry.get('range'))
        except InvalidInput:return False
    return True

def enforce_protection(original,updated,role):
    if role=='owner':return
    protections=original.get('protectedRanges',[])
    if protections!=updated.get('protectedRanges',[]):raise PermissionError('Somente o proprietário pode alterar os intervalos protegidos.')
    if not protections:return
    old,new=original.get('workbook',{}),updated.get('workbook',{})
    if old.get('resources')!=new.get('resources'):raise PermissionError('Somente o proprietário altera regras em uma planilha com intervalos protegidos.')
    for rule in protections:
        a=old.get('sheets',{}).get(rule['sheetId']);b=new.get('sheets',{}).get(rule['sheetId'])
        if a is None:continue
        if b is None or any(a.get(key)!=b.get(key) for key in ('rowCount','columnCount','mergeData')):raise PermissionError('A estrutura desta aba contém células protegidas.')
        x1,y1,x2,y2=bounds(rule['range'])
        def protected_links(content):
            result={}
            for link in content.get('links',[]):
                if link['sheetId']!=rule['sheetId']:continue
                x,y,_,_=bounds(link['cell'])
                if x1<=x<=x2 and y1<=y<=y2:result[link['cell']]=link
            return result
        if protected_links(original)!=protected_links(updated):raise PermissionError('Vínculo em célula protegida.')
        for row in range(y1,y2+1):
            if a.get('rowData',{}).get(str(row))!=b.get('rowData',{}).get(str(row)):raise PermissionError('Linha protegida.')
            for col in range(x1,x2+1):
                cell_a=a.get('cellData',{}).get(str(row),{}).get(str(col));cell_b=b.get('cellData',{}).get(str(row),{}).get(str(col))
                if cell_a!=cell_b:raise PermissionError('Intervalo protegido: '+rule['range']+'. Desfaça a alteração para salvar.')
                style=(cell_a or {}).get('s')
                if isinstance(style,str) and old.get('styles',{}).get(style)!=new.get('styles',{}).get(style):raise PermissionError('Formatação de célula protegida.')
        for col in range(x1,x2+1):
            if a.get('columnData',{}).get(str(col))!=b.get('columnData',{}).get(str(col)):raise PermissionError('Coluna protegida.')
