"""Bounded Office file exchange. No macros, external links or remote fetches."""
import base64
import binascii
import io
import json
import math
import re
import zipfile
from datetime import date, datetime
from pathlib import Path, PurePath
from server.store import InvalidInput

MAX_FILE = 2_500_000
MIMES = {
    'ics': 'text/calendar; charset=utf-8',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
}
FORMATS = {'calendar': 'ics', 'document': 'docx', 'note': 'docx', 'sheet': 'xlsx', 'table': 'xlsx', 'slides': 'pptx'}
ALIASES = json.loads(Path(__file__).with_name('formula_aliases.json').read_text())


def excel_formula(value):
    parts = re.split(r'''("(?:[^"]|"")*"|'(?:[^']|'')*')''', value)
    for i, part in enumerate(parts):
        if part.startswith(('"', "'")):
            continue
        parts[i] = re.sub(r'[\w.]+(?=\s*\()', lambda m: ALIASES.get(m[0].upper(), m[0]), part).replace(';', ',')
    return ''.join(parts)


def _archive(data):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            entries = z.infolist()
            if len(entries) > 1500 or sum(f.file_size for f in entries) > 24_000_000:
                raise InvalidInput('Arquivo expandido maior que o limite de 24 MB.')
            for entry in entries:
                name = entry.filename.lower()
                if entry.flag_bits & 1 or 'vbaproject' in name or name.startswith('/') or '..' in name.split('/'):
                    raise InvalidInput('Arquivo protegido, macro ou caminho não permitido.')
                if entry.file_size > 8_000_000:
                    raise InvalidInput('Uma parte do arquivo excede o limite de 8 MB.')
                if name.endswith(('.xml', '.rels')):
                    xml = z.read(entry)
                    if re.search(br'<!\s*(DOCTYPE|ENTITY)', xml, re.I):
                        raise InvalidInput('Declarações XML externas não são permitidas.')
            if z.testzip() is not None:
                raise InvalidInput('Arquivo Office corrompido.')
    except (zipfile.BadZipFile, RuntimeError, OSError):
        raise InvalidInput('Arquivo Office inválido ou corrompido.') from None


def _cell_text(value):
    if value is None:
        return ''
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    return str(value)


def import_file(name, encoded):
    if not isinstance(name, str) or not isinstance(encoded, str) or len(encoded) > 3_400_000:
        raise InvalidInput('Envie um arquivo Office de até 2,5 MB.')
    ext = PurePath(name).suffix.lower().lstrip('.')
    if ext not in MIMES:
        raise InvalidInput('Formatos aceitos: DOCX, XLSX, PPTX e ICS, sem macros.')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise InvalidInput('Arquivo codificado incorretamente.') from None
    if not data or len(data) > MAX_FILE:
        raise InvalidInput('Envie um arquivo Office de até 2,5 MB.')
    if ext == 'ics':
        from server.calendar_io import import_calendar
        return {'title':(PurePath(name).stem or 'Agenda')[:200], 'kind':'calendar', 'content':import_calendar(data)}, ['Recorrências foram convertidas em ocorrências individuais. Convites, participantes e alarmes não são sincronizados. Horários sem fuso são interpretados como UTC.']
    _archive(data)
    stream = io.BytesIO(data)
    warnings = []
    try:
        if ext == 'docx':
            from docx import Document
            document = Document(stream)
            lines = []
            for block in document.iter_inner_content():
                if hasattr(block, 'rows'):
                    for row in block.rows:
                        lines.append(' | '.join(cell.text for cell in row.cells))
                else:
                    prefix = ''
                    if block.style and block.style.name.startswith('Heading '):
                        level = block.style.name.split()[-1]
                        prefix = '#' * min(3, int(level)) + ' ' if level.isdigit() else ''
                    text = ''.join(('**' + run.text + '**' if run.bold else '*' + run.text + '*' if run.italic else run.text) for run in block.runs)
                    lines.append(prefix + (text or block.text))
            kind, content = 'document', {'text': '\n'.join(lines)}
            warnings.append('Texto, títulos e tabelas foram importados; imagens e layout de página não são preservados.')
        elif ext == 'xlsx':
            from server.spreadsheet_io import import_workbook
            kind, content = 'sheet', import_workbook(stream)
            warnings.append('Abas, valores, fórmulas, estilos, mesclagens, dimensões e painéis congelados foram importados. Filtros por valores, validações comuns e regras condicionais numéricas/por fórmula também são importados. Gráficos, tabelas dinâmicas, macros e regras avançadas do XLSX não são importados.')
        else:
            from pptx import Presentation
            presentation = Presentation(stream)
            if not 1 <= len(presentation.slides) <= 100:
                raise InvalidInput('A apresentação deve ter de 1 a 100 slides.')
            slides = []
            for slide in presentation.slides:
                title = slide.shapes.title
                body = '\n'.join(shape.text for shape in slide.shapes if shape.has_text_frame and shape != title and not shape.name.startswith('DRAP '))
                notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide and slide.notes_slide.notes_text_frame else ''
                entry={'title': title.text if title is not None else '', 'body': body, 'notes': notes}
                from server.slides_io import import_objects
                objects=import_objects(slide,presentation)
                if objects:entry['objects']=objects
                slides.append(entry)
            kind, content = 'slides', {'slides': slides}
            warnings.append('Títulos, textos, notas e imagens foram importados. Objetos de texto e formas criados no DRAP também são preservados. Animações, vídeos, grupos, recortes e temas externos não são preservados.')
    except InvalidInput:
        raise
    except Exception:
        raise InvalidInput('Não foi possível ler este arquivo Office. Verifique o formato e se ele não está protegido.') from None
    return {'title': (PurePath(name).stem.strip() or 'Importação')[:200], 'kind': kind, 'content': content}, warnings


def export_file(item, extension):
    if FORMATS.get(item['kind']) != extension:
        raise InvalidInput('Formato incompatível com esta ferramenta.')
    if extension == 'ics':
        from server.calendar_io import export_calendar
        result = export_calendar(item)
        if len(result) > 4_000_000: raise InvalidInput('A exportação excede o limite de 4 MB.')
        return result, MIMES['ics']
    content = item['content']
    output = io.BytesIO()
    if extension == 'docx':
        from docx import Document
        document = Document()
        document.core_properties.title = item['title']
        document.core_properties.author = 'DRAP office'
        for line in content['text'].splitlines():
            heading = re.match(r'^(#{1,3})\s+(.*)', line)
            if heading:
                paragraph = document.add_heading('', level=len(heading[1]))
                line = heading[2]
            else:
                paragraph = document.add_paragraph()
            for part in re.split(r'(\*\*.*?\*\*|\*[^*]+\*)', line):
                run = paragraph.add_run(part[2:-2] if part.startswith('**') and part.endswith('**') else part[1:-1] if part.startswith('*') and part.endswith('*') else part)
                if part.startswith('**') and part.endswith('**'):
                    run.bold = True
                elif part.startswith('*') and part.endswith('*'):
                    run.italic = True
        document.save(output)
    elif extension == 'xlsx' and 'workbook' in content:
        from server.spreadsheet_io import export_workbook
        export_workbook(content['workbook'], output, content.get('charts',[]), content.get('pivots',[]))
    elif extension == 'xlsx':
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        workbook = Workbook()
        workbook.remove(workbook.active)
        if item['kind'] == 'table':
            sheets = [{'name': 'Dados', 'cells': [content['columns'], *content['rows']]}]
        else:
            sheets = content.get('sheets') or [{'name': 'Planilha 1', 'cells': content['cells']}]
        for entry in sheets:
            sheet = workbook.create_sheet(entry['name'])
            for r, row in enumerate(entry['cells'], 1):
                for c, value in enumerate(row, 1):
                    cell = sheet.cell(r, c)
                    # Preserve literals rather than turning imported text into formulas.
                    cell.value = excel_formula(value) if item['kind'] == 'sheet' and value.startswith('=') else value
                    numeric = (item['kind'] == 'sheet' or (r > 1 and content.get('types', [])[c-1:c] == ['number'])) and re.fullmatch(r'[-+]?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][-+]?\d+)?', value)
                    if numeric and math.isfinite(float(value)):
                        cell.value = float(value)
                    elif item['kind'] == 'table' or not value.startswith('='):
                        cell.data_type = 's'
                    if r == 1:
                        cell.font = Font(bold=True, color='FFFFFF')
                        cell.fill = PatternFill('solid', fgColor='4B5320')
            sheet.freeze_panes = 'A2'
            sheet.auto_filter.ref = sheet.dimensions
        workbook.save(output)
    else:
        from server.slides_io import export_slides
        export_slides(content,item['title'],output)
    result = output.getvalue()
    if len(result) > 4_000_000:
        raise InvalidInput('A exportação excede o limite de 4 MB.')
    return result, MIMES[extension]
