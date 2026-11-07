"""Bounded JSON contracts for every editor, including imported content."""
from datetime import datetime, timezone
import math
import re
from server.store import InvalidInput
from server.rich_document import valid_rich,valid_tabs
from server.pivots import valid_pivots
from server.attachments import valid_attachments
from server.document_io import valid_images, valid_page
from server.slides_io import valid_objects, valid_slide_options


DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def valid_task_schedule(t):
    """Optional scheduling fields of a board task."""
    # Older and imported boards may hold free-form deadlines; only new fields are strict.
    start = t.get('start', '')
    if not isinstance(start, str) or (start and not DATE.match(start)) or len(t.get('due', '')) > 40:
        return False
    if 'milestone' in t and type(t['milestone']) is not bool:
        return False
    if t.get('milestone') and not t.get('due'):
        return False
    if start and DATE.match(t.get('due', '')) and not t.get('milestone') and start > t['due']:
        return False
    for field in ('plannedHours', 'actualHours', 'hourlyRate', 'fixedCost'):
        value = t.get(field, 0)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100_000:
            return False
    task_id = t.get('id', '')
    depends = t.get('depends', t.get('dependsOn', []))
    return (isinstance(task_id, str) and len(task_id) <= 100 and isinstance(depends, list) and len(depends) <= 50
            and all(isinstance(d, str) and len(d) <= 100 for d in depends))


def valid_task_graph(tasks):
    """Task ids are unique, dependencies point to existing tasks and form no cycle."""
    ids = [t.get('id') for t in tasks if t.get('id')]
    if len(ids) != len(set(ids)):
        return False
    graph = {t['id']: t.get('depends', t.get('dependsOn', [])) for t in tasks if t.get('id')}
    if any(t.get('depends') and not t.get('id') for t in tasks):
        return False
    if any(d not in graph or d == node for node, deps in graph.items() for d in deps):
        return False
    state = {}
    for root in graph:
        if root in state:
            continue
        stack = [(root, iter(graph[root]))]
        state[root] = 1
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                state[node] = 2
                stack.pop()
            elif state.get(child) == 1:
                return False
            elif child not in state:
                state[child] = 1
                stack.append((child, iter(graph[child])))
    return True


def valid_form_field(f):
    kind = f.get('type')
    if kind not in ('text', 'longtext', 'rating', 'email', 'number', 'date', 'choice', 'multiple', 'scale') or type(f.get('required')) is not bool:
        return False
    options = f.get('options', [])
    if not isinstance(options, list) or len(options) > 50 or not all(isinstance(o, str) and len(o) <= 200 for o in options):
        return False
    if kind == 'multiple' and any(';' in o for o in options):
        return False
    if 'max' in f and not (type(f['max']) is int and 2 <= f['max'] <= 10):
        return False
    if 'points' in f and not (type(f['points']) is int and 0 <= f['points'] <= 100):
        return False
    correct = f.get('correct', '')
    if kind == 'multiple':
        return isinstance(correct, list) and len(correct) <= 50 and all(o in options for o in correct) if 'correct' in f else True
    return isinstance(correct, str) and len(correct) <= 4000


CELL = re.compile(r'^[A-Z]{1,3}[1-9][0-9]{0,5}$')


def valid_sheet_links(links):
    """Cells linked to another DRAP file or to an external https address."""
    if not isinstance(links, list) or len(links) > 200:
        return False
    seen = set()
    for link in links:
        if not isinstance(link, dict) or not isinstance(link.get('sheetId'), str) or len(link['sheetId']) > 100:
            return False
        if not isinstance(link.get('cell'), str) or not CELL.match(link['cell']):
            return False
        key = (link['sheetId'], link['cell'])
        if key in seen:
            return False
        seen.add(key)
        if link.get('type') == 'item':
            if not (isinstance(link.get('item'), str) and 0 < len(link['item']) <= 64
                    and isinstance(link.get('title', ''), str) and len(link.get('title', '')) <= 200
                    and isinstance(link.get('kind', ''), str) and len(link.get('kind', '')) <= 20):
                return False
            if set(link) - {'type', 'item', 'title', 'kind', 'sheetId', 'cell'}:
                return False
        elif link.get('type') == 'url':
            url = link.get('url')
            if not (isinstance(url, str) and url.startswith('https://') and len(url) <= 2000) or set(link) - {'type', 'url', 'sheetId', 'cell'}:
                return False
        else:
            return False
    return True


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

    if not isinstance(c, dict) or not valid_attachments(c.get("attachments", [])):
        return False
    if kind in ('document', 'note'):
        return isinstance(c.get('text'), str) and valid_images(c.get('images',[])) and valid_page(c.get('page',{})) and ('rich' not in c or valid_rich(c['rich'])) and valid_tabs(c) and all(isinstance(c.get(k, ''), str) and len(c.get(k, '')) <= 200 for k in ('header', 'footer')) and type(c.get('pageNumbers', False)) is bool
    if kind == 'sheet':
        from server.sheet_protection import valid_protection
        if not valid_protection(c):return False
        if not valid_pivots(c.get('pivots',[])):return False
        if not valid_sheet_links(c.get('links', [])):return False
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
        return valid_slide_options(c.get('master',{})) and c.get('theme', 'light') in ('light', 'army', 'navy') and bool(c.get('slides')) and objects(c.get('slides'), lambda s: all(isinstance(s.get(k), str) for k in ('title', 'body', 'notes')) and valid_objects(s.get('objects',[])) and valid_slide_options(s), 100)
    if kind == 'board':
        from server.project_tools import validate_dependencies, valid_planning
        if not valid_planning(c):return False
        if not isinstance(c.get('tasks'),list) or any(not isinstance(task,dict) for task in c['tasks']):return False
        try:
            if not validate_dependencies(c['tasks']):return False
        except InvalidInput:return False
        return objects(c.get('tasks'), lambda t: isinstance(t.get('title'), str) and isinstance(t.get('due'), str)
                       and t.get('status') in ('A fazer', 'Em andamento', 'Concluído')
                       and t.get('priority', 'Normal') in ('Baixa', 'Normal', 'Alta', 'Urgente')
                       and isinstance(t.get('assignee', ''), str) and len(t.get('assignee', '')) <= 100
                       and objects(t.get('subtasks', []), lambda s: isinstance(s.get('title'), str) and 1 <= len(s['title']) <= 200 and type(s.get('done')) is bool, 50)
                       and valid_task_schedule(t)) and valid_task_graph(c['tasks'])
    if kind == 'calendar':
        return objects(c.get('events'), lambda e: isinstance(e.get('title'), str) and timestamp(e.get('start')) and timestamp(e.get('end')) and event_duration_positive(e['start'],e['end'])
                       and isinstance(e.get('location', ''), str) and len(e.get('location', '')) <= 500
                       and isinstance(e.get('description', ''), str) and len(e.get('description', '')) <= 4000)
    if kind == 'form':
        from server.forms import valid_quiz
        if not valid_quiz(c):return False
        return (strings(c.get('questions'), 100)
                and type(c.get('quiz', False)) is bool
                and ('fields' not in c or (isinstance(c['fields'], list) and len(c['fields']) == len(c['questions']) and objects(c['fields'], valid_form_field, 100)))
                and objects(c.get('responses'), lambda r: type(r.get('at')) in (int, float) and strings(r.get('answers'), 100) and strings(r.get('questions'), 100) and len(r['answers']) == len(r['questions'])
                            and all(k not in r or (type(r[k]) in (int, float) and math.isfinite(r[k]) and 0 <= r[k] <= 10000) for k in ('score', 'total'))))
    if kind == 'table':
        from server.table_relations import valid_relations
        if not (strings(c.get('columns'), 26) and bool(c['columns']) and matrix(c.get('rows')) and all(len(r) == len(c['columns']) for r in c['rows'])):
            return False
        if not valid_relations(c):return False
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
                and ('shapes' not in c or (isinstance(c['shapes'],list) and len(c['shapes'])==len(c['nodes']) and all(isinstance(s,str) and s in ('process','decision','terminator','database','document') for s in c['shapes'])))
                and ('positions' not in c or (objects(c['positions'], lambda p: all(type(p.get(k)) in (int, float) and 0 <= p[k] <= 2000 for k in ('x', 'y')), 100) and len(c['positions']) == len(c['nodes'])))
                and ('edges' not in c or objects(c['edges'], lambda e: all(type(e.get(k)) is int and 0 <= e[k] < len(c['nodes']) for k in ('from', 'to')) and isinstance(e.get('label',''),str) and len(e.get('label','')) <= 100, 300)))
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

CHART_TYPES=('bar','stacked','hbar','line','area','pie','doughnut','scatter','horizontal','radar')


def valid_charts(charts,book):
    if not isinstance(charts,list) or len(charts)>10:return False
    ids=set()
    for chart in charts:
        if not isinstance(chart,dict) or chart.get('type') not in CHART_TYPES:return False
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
        width=x2-x1
        if not 1<=width<=6 or (chart['type'] in ('pie','doughnut') and width!=1) or not 0<y2-y1<=200 or x2>1024 or y2>100000:return False
    return True


def event_duration_positive(start,end):
    def instant(value):
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return instant(end)>instant(start)
