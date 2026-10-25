"""Bounded JSON contracts for every editor, including imported content."""
from datetime import datetime
import math
import re
from server.store import InvalidInput
from server.pivots import valid_pivots
from server.slides_io import valid_objects


def valid_content(kind, c):
    def strings(values, maximum=200):
        return isinstance(values, list) and len(values) <= maximum and all(isinstance(v, str) for v in values)

    def matrix(rows):
        return isinstance(rows, list) and len(rows) <= 200 and all(strings(r, 26) for r in rows)

    def grid(rows):
        return matrix(rows) and bool(rows) and bool(rows[0]) and all(len(r) == len(rows[0]) for r in rows)

    def objects(values, predicate, maximum=1000):
        return isinstance(values, list) and len(values) <= maximum and all(isinstance(v, dict) and predicate(v) for v in values)

    def timestamp(value):
        if not isinstance(value, str):
            return False
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False

    if not isinstance(c, dict):
        return False
    if kind in ('document', 'note'):
        return isinstance(c.get('text'), str)
    if kind == 'sheet':
        if not valid_pivots(c.get('pivots',[])):return False
        if 'workbook' in c:
            return valid_workbook(c['workbook']) and valid_charts(c.get('charts',[]),c['workbook'])
        rows = c.get('cells')
        if not grid(rows):
            return False
        if 'sheets' not in c:
            return True
        sheets = c['sheets']
        if not objects(sheets, lambda s: isinstance(s.get('name'), str) and 1 <= len(s['name']) <= 31 and not any(ch in s['name'] for ch in '[]:*?/\\') and grid(s.get('cells')), 12) or not sheets:
            return False
        active = c.get('activeSheet', 0)
        return (type(active) is int and 0 <= active < len(sheets)
                and len({s['name'].casefold() for s in sheets}) == len(sheets)
                and rows == sheets[active]['cells'])
    if kind == 'slides':
        return c.get('theme', 'light') in ('light', 'army', 'navy') and bool(c.get('slides')) and objects(c.get('slides'), lambda s: all(isinstance(s.get(k), str) for k in ('title', 'body', 'notes')) and valid_objects(s.get('objects',[])), 100)
    if kind == 'board':
        return objects(c.get('tasks'), lambda t: isinstance(t.get('title'), str) and isinstance(t.get('due'), str)
                       and t.get('status') in ('A fazer', 'Em andamento', 'Concluído')
                       and t.get('priority', 'Normal') in ('Baixa', 'Normal', 'Alta', 'Urgente')
                       and isinstance(t.get('assignee', ''), str) and len(t.get('assignee', '')) <= 100
                       and objects(t.get('subtasks', []), lambda s: isinstance(s.get('title'), str) and 1 <= len(s['title']) <= 200 and type(s.get('done')) is bool, 50))
    if kind == 'calendar':
        return objects(c.get('events'), lambda e: isinstance(e.get('title'), str) and timestamp(e.get('start')) and timestamp(e.get('end')) and e['start'] < e['end']
                       and isinstance(e.get('location', ''), str) and len(e.get('location', '')) <= 500
                       and isinstance(e.get('description', ''), str) and len(e.get('description', '')) <= 4000)
    if kind == 'form':
        return (strings(c.get('questions'), 100)
                and ('fields' not in c or (isinstance(c['fields'], list) and len(c['fields']) == len(c['questions']) and objects(c['fields'], lambda f:
                    f.get('type') in ('text', 'email', 'number', 'date', 'choice') and type(f.get('required')) is bool
                    and strings(f.get('options', []), 50), 100)))
                and objects(c.get('responses'), lambda r: type(r.get('at')) in (int, float) and strings(r.get('answers'), 100) and strings(r.get('questions'), 100) and len(r['answers']) == len(r['questions'])))
    if kind == 'table':
        if not (strings(c.get('columns'), 26) and bool(c['columns']) and matrix(c.get('rows')) and all(len(r) == len(c['columns']) for r in c['rows'])):
            return False
        types = c.get('types', ['text'] * len(c['columns']))
        if not strings(types, 26) or len(types) != len(c['columns']) or any(t not in ('text', 'number', 'date', 'email') for t in types):
            return False
        try:
            for row in c['rows']:
                for value, field_type in zip(row, types):
                    if not value:
                        continue
                    if field_type == 'number' and not math.isfinite(float(value)):
                        return False
                    if field_type == 'date':
                        datetime.strptime(value, '%Y-%m-%d')
                    if field_type == 'email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
                        return False
        except ValueError:
            return False
        return True
    if kind == 'diagram':
        return (strings(c.get('nodes'), 100)
                and ('positions' not in c or (objects(c['positions'], lambda p: all(type(p.get(k)) in (int, float) and 0 <= p[k] <= 2000 for k in ('x', 'y')), 100) and len(c['positions']) == len(c['nodes'])))
                and ('edges' not in c or objects(c['edges'], lambda e: all(type(e.get(k)) is int and 0 <= e[k] < len(c['nodes']) for k in ('from', 'to')), 300)))
    if kind == 'portal':
        return isinstance(c.get('text'), str) and strings(c.get('links'), 100)
    return False


def validate_content(kind, content):
    if not valid_content(kind, content):
        raise InvalidInput('Conteúdo incompatível com a ferramenta ou limite excedido.')


def valid_workbook(book):
    """Bound native workbook coordinates and sparse payload before persistence."""
    if not isinstance(book, dict) or not isinstance(book.get('id'), str): return False
    order, sheets, styles = book.get('sheetOrder'), book.get('sheets'), book.get('styles', {})
    if not isinstance(order, list) or not 1 <= len(order) <= 20 or not all(isinstance(k,str) for k in order): return False
    if len(set(order)) != len(order) or not isinstance(sheets,dict) or set(order) != set(sheets): return False
    if not isinstance(styles,dict) or len(styles)>10000: return False
    names=set(); count=0
    def index(k,maximum): return isinstance(k,str) and k.isdecimal() and len(k)<=6 and 0<=int(k)<maximum
    for key in order:
        sheet=sheets[key]
        if not isinstance(sheet,dict) or sheet.get('id')!=key: return False
        name=sheet.get('name')
        if not isinstance(name,str) or not 1<=len(name)<=31 or name.casefold() in names or any(ch in name for ch in '[]:*?/\\'): return False
        names.add(name.casefold())
        rows,cols=sheet.get('rowCount'),sheet.get('columnCount')
        if type(rows) is not int or not 1<=rows<=100000 or type(cols) is not int or not 1<=cols<=1024:return False
        data=sheet.get('cellData',{})
        if not isinstance(data,dict):return False
        for r,cells in data.items():
            if not index(r,rows) or not isinstance(cells,dict):return False
            for c,cell in cells.items():
                if not index(c,cols):return False
                if cell is None:continue
                count+=1
                if count>50000 or not isinstance(cell,dict):return False
                if 'v' in cell and cell['v'] is not None and type(cell['v']) not in (str,int,float,bool):return False
                if 'f' in cell and cell['f'] is not None and (not isinstance(cell['f'],str) or len(cell['f'])>8192):return False
                if cell.get('s') is not None and not isinstance(cell['s'],(str,dict)):return False
        merges=sheet.get('mergeData',[])
        if not isinstance(merges,list) or len(merges)>10000:return False
        for m in merges:
            if not isinstance(m,dict) or not all(type(m.get(k)) is int for k in ('startRow','endRow','startColumn','endColumn')):return False
            if not 0<=m['startRow']<=m['endRow']<rows or not 0<=m['startColumn']<=m['endColumn']<cols:return False
        for field,limit in [('rowData',rows),('columnData',cols)]:
            values=sheet.get(field,{})
            if not isinstance(values,dict) or not all(index(k,limit) and (v is None or isinstance(v,dict)) for k,v in values.items()):return False
    resources=book.get('resources',[])
    return isinstance(resources,list) and len(resources)<=50 and all(isinstance(r,dict) and isinstance(r.get('name'),str) and isinstance(r.get('data'),str) for r in resources)

def valid_charts(charts,book):
    if not isinstance(charts,list) or len(charts)>10:return False
    ids=set()
    for chart in charts:
        if not isinstance(chart,dict) or chart.get('type') not in ('bar','line','pie'):return False
        if not isinstance(chart.get('id'),str) or chart['id'] in ids or len(chart['id'])>100:return False
        ids.add(chart['id'])
        if not isinstance(chart.get('title'),str) or not 1<=len(chart['title'])<=100:return False
        sid=chart.get('sheetId')
        # A removed sheet leaves a recoverable broken chart definition in the UI.
        if not isinstance(sid,str) or len(sid)>100:return False
        match=re.fullmatch(r'([A-Z]{1,3})([1-9]\d{0,5}):([A-Z]{1,3})([1-9]\d{0,5})',str(chart.get('range','')))
        if not match:return False
        def col(s):
            n=0
            for c in s:n=n*26+ord(c)-64
            return n
        c1,r1,c2,r2=match.groups();x1,x2=col(c1),col(c2);y1,y2=int(r1),int(r2)
        if x2-x1!=1 or not 0<y2-y1<=200 or x2>1024 or y2>100000:return False
    return True
