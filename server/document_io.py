"""Document exchange preserves supported tables, lists, links and embedded raster images."""
import base64,io,re
from PIL import Image
from markdown_it import MarkdownIt
INLINE_MARKDOWN=MarkdownIt('commonmark')
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Inches, Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from server.slides_io import image_bytes
from server.store import InvalidInput


def valid_page(page):
    if not isinstance(page,dict):return False
    enums={'size':('A4','Letter'),'orientation':('portrait','landscape'),'font':('Arial','Georgia','Times New Roman','Courier New'),'align':('left','center','right','justify'),'mode':('page','wide')}
    for key,values in enums.items():
        if key in page and page[key] not in values:return False
    for key,low,high in [('margin',5,40),('fontSize',8,36),('lineHeight',1,2)]:
        if key in page and (type(page[key]) not in (int,float) or not low<=page[key]<=high):return False
    for key in ('header','footer'):
        if key in page and (not isinstance(page[key],str) or len(page[key])>500):return False
    if 'pageNumbers' in page and type(page['pageNumbers']) is not bool:return False
    return True


def valid_images(images):
    if not isinstance(images,list) or len(images)>20:return False
    ids=set()
    for image in images:
        if not isinstance(image,dict) or not isinstance(image.get('id'),str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',image['id']) or image['id'] in ids:return False
        ids.add(image['id'])
        if not isinstance(image.get('alt',''),str) or len(image.get('alt',''))>200:return False
        if type(image.get('width',80)) not in (int,float) or not 10<=image.get('width',80)<=100:return False
        try:image_bytes(image.get('src'))
        except InvalidInput:return False
    return True


def inline(paragraph,text):
    tokens=INLINE_MARKDOWN.parseInline(text)[0].children or []
    bold=italic=0;link=None
    for token in tokens:
        if token.type=='strong_open':bold+=1;continue
        if token.type=='strong_close':bold=max(0,bold-1);continue
        if token.type=='em_open':italic+=1;continue
        if token.type=='em_close':italic=max(0,italic-1);continue
        if token.type=='link_open':
            url=token.attrGet('href') or '';link=url if url.startswith(('http://','https://')) else None;continue
        if token.type=='link_close':link=None;continue
        value='\n' if token.type in ('softbreak','hardbreak') or (token.type=='html_inline' and re.fullmatch(r'<br\s*/?>',token.content,re.I)) else token.content
        if not value:continue
        run=paragraph.add_run(value);run.bold=bool(bold);run.italic=bool(italic)
        if token.type=='code_inline':run.font.name='Courier New'
        if link:
            h=OxmlElement('w:hyperlink');h.set(qn('r:id'),paragraph.part.relate_to(link,RT.HYPERLINK,is_external=True));h.append(run._r);paragraph._p.append(h)


def export_document(content,title,output):
    if content.get('tabs'):
        from server.rich_document import import_rich
        combined=[]
        for index,tab in enumerate(content['tabs']):
            if index:combined.append({'type':'pageBreak'})
            combined.append({'type':'heading','attrs':{'level':1},'content':[{'type':'text','text':tab['name']}]})
            rich=tab.get('rich')
            if not rich:
                temporary=io.BytesIO();export_document({'text':tab['text'],'images':content.get('images',[])},tab['name'],temporary);temporary.seek(0);rich=import_rich(Document(temporary),content.get('images',[]))
            combined.extend(rich['content'])
        content={**content,'rich':{'type':'doc','content':combined}}
    document=Document();document.core_properties.title=title;document.core_properties.author='DRAP office'
    settings=content.get('page',{})
    if settings:
        section=document.sections[0];width,height=(210,297) if settings.get('size','A4')=='A4' else (215.9,279.4)
        if settings.get('orientation')=='landscape':width,height=height,width;section.orientation=WD_ORIENT.LANDSCAPE
        section.page_width=Mm(width);section.page_height=Mm(height)
        section.top_margin=section.bottom_margin=section.left_margin=section.right_margin=Mm(settings.get('margin',20))
        normal=document.styles['Normal'];normal.font.name=settings.get('font','Arial');normal.font.size=Pt(settings.get('fontSize',12))
        normal.paragraph_format.line_spacing=settings.get('lineHeight',1.5)
        normal.paragraph_format.alignment={'left':WD_ALIGN_PARAGRAPH.LEFT,'center':WD_ALIGN_PARAGRAPH.CENTER,'right':WD_ALIGN_PARAGRAPH.RIGHT,'justify':WD_ALIGN_PARAGRAPH.JUSTIFY}[settings.get('align','left')]
    page_setup(document,{key:settings.get(key,content.get(key)) for key in ('header','footer','pageNumbers')})
    if content.get('rich'):
        from server.rich_document import export_rich
        export_rich(document,content['rich'],{im['id']:im for im in content.get('images',[])})
        document.save(output)
        return
    lines=content['text'].splitlines();images={im['id']:im for im in content.get('images',[])};i=0
    def cells(line):return [x.strip().replace('\\|','|') for x in re.split(r'(?<!\\)\|',line.strip().strip('|'))]
    while i<len(lines):
        line=lines[i];i+=1
        picture=re.fullmatch(r'!\[([^\]]*)\]\(drap-image:([a-zA-Z0-9_-]+)\)',line.strip())
        if picture:
            im=images.get(picture[2])
            if not im:raise InvalidInput('Uma imagem referenciada no documento não está disponível.')
            data=image_bytes(im['src'])
            with Image.open(io.BytesIO(data)) as raster:width=min(6.5*im.get('width',80)/100,8.5*raster.width/raster.height)
            shape=document.add_picture(io.BytesIO(data),width=Inches(width));shape._inline.docPr.set('descr',im.get('alt',picture[1]));continue
        if '|' in line and i<len(lines) and re.match(r'^\s*\|?\s*:?-{3,}',lines[i]):
            headers=cells(line);i+=1;rows=[]
            while i<len(lines) and '|' in lines[i]:rows.append(cells(lines[i]));i+=1
            if len(headers)>100 or (len(rows)+1)*len(headers)>50000:raise InvalidInput('Tabela do documento excede 50 mil células ou 100 colunas.')
            table=document.add_table(rows=1,cols=len(headers));table.style='Table Grid'
            for cell,value in zip(table.rows[0].cells,headers):inline(cell.paragraphs[0],value)
            for row in rows:
                for cell,value in zip(table.add_row().cells,row):inline(cell.paragraphs[0],value)
            continue
        if re.fullmatch(r'\s*(-{3,}|\*{3,}|_{3,})\s*',line):
            document.add_page_break();continue
        heading=re.match(r'^(#{1,3})\s+(.*)',line);bullet=re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)',line)
        if heading:p=document.add_heading('',level=len(heading[1]));line=heading[2]
        elif bullet:
            nested=' 2' if len(bullet[1].expandtabs(2))>=2 else ''
            p=document.add_paragraph(style=('List Number' if bullet[2][0].isdigit() else 'List Bullet')+nested);line=bullet[3]
        else:p=document.add_paragraph()
        inline(p,line)
    document.save(output)


def _page_field(paragraph,instruction):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    run=paragraph.add_run()
    for kind,text in (('begin',None),(None,instruction),('separate',None),(None,'1'),('end',None)):
        if kind:
            element=OxmlElement('w:fldChar');element.set(qn('w:fldCharType'),kind)
        elif text=='1':
            element=OxmlElement('w:t');element.text=text
        else:
            element=OxmlElement('w:instrText');element.set(qn('xml:space'),'preserve');element.text=text
        run._r.append(element)


def page_setup(document,content):
    """Header, footer and 'Página X de Y' on every page of the DOCX."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    section=document.sections[0]
    if content.get('header'):
        paragraph=section.header.paragraphs[0];paragraph.text=content['header'];paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
    if content.get('footer') or content.get('pageNumbers'):
        paragraph=section.footer.paragraphs[0]
        if content.get('footer'):paragraph.add_run(content['footer']+('   ·   ' if content.get('pageNumbers') else ''))
        if content.get('pageNumbers'):
            paragraph.add_run('Página ');_page_field(paragraph,'PAGE');paragraph.add_run(' de ');_page_field(paragraph,'NUMPAGES')
        paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER


def import_document(stream):
    document=Document(stream);lines=[];images=[]
    def text(paragraph):
        result=[]
        for part in paragraph.iter_inner_content():
            if hasattr(part,'url'):
                result.append('['+part.text+']('+part.url.replace(')','%29')+')' if part.url.startswith(('http://','https://')) else part.text)
            else:
                value=re.sub(r'([\\`*_\[\]])',r'\\\1',part.text)
                marker='***' if part.bold and part.italic else '**' if part.bold else '*' if part.italic else ''
                result.append(marker+value+marker if value else '')
        return ''.join(result)
    for block in document.iter_inner_content():
        if hasattr(block,'rows'):
            rows=[[cell.text.replace('|','\\|').replace('\n','<br>') for cell in row.cells] for row in block.rows]
            if rows:lines.extend(['| '+' | '.join(rows[0])+' |','| '+' | '.join('---' for _ in rows[0])+' |',*['| '+' | '.join(row)+' |' for row in rows[1:]]])
            continue
        prefix=''
        if block.style:
            name=block.style.name
            if name.startswith('Heading ') and name.split()[-1].isdigit():prefix='#'*min(3,int(name.split()[-1]))+' '
            elif name.startswith('List Bullet'):prefix='- '
            elif name.startswith('List Number'):prefix='1. '
        value=text(block)
        drawings=block._p.xpath('.//w:drawing')
        if value or not drawings:lines.append(prefix+value)
        for drawing in drawings:
            blips=drawing.xpath('.//a:blip')
            for blip in blips:
                rid=blip.get(qn('r:embed'))
                if not rid:continue
                if len(images)>=20:raise InvalidInput('O documento excede 20 imagens.')
                blob=document.part.related_parts[rid].blob
                with Image.open(io.BytesIO(blob)) as im:
                    if im.width*im.height>40_000_000:raise InvalidInput('Imagem do documento excede 40 megapixels.')
                    im=im.convert('RGBA');im.thumbnail((1200,1200));out=io.BytesIO();im.save(out,format='PNG',optimize=True)
                    while len(out.getvalue())>300000 and min(im.size)>100:
                        im.thumbnail((int(im.width*.8),int(im.height*.8)));out=io.BytesIO();im.save(out,format='PNG',optimize=True)
                props=drawing.xpath('.//wp:docPr');alt=(props[0].get('descr','') if props else '')[:200]
                key='docx-'+str(len(images));image={'id':key,'src':'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode(),'alt':alt,'width':80,'ratio':im.width/im.height}
                images.append(image);lines.append('!['+alt.replace(']','')+'](drap-image:'+key+')')
    if not valid_images(images):raise InvalidInput('Uma imagem do documento excede os limites.')
    section=document.sections[0];normal=document.styles['Normal']
    page_width=section.page_width or Mm(210);page_height=section.page_height or Mm(297);margin=section.left_margin or Mm(20)
    result={'text':'\n'.join(lines),'page':{'size':'Letter' if abs(min(page_width.mm,page_height.mm)-215.9)<2 else 'A4','orientation':'landscape' if page_width>page_height else 'portrait','margin':max(5,min(40,round(margin.mm))), 'font':normal.font.name if normal.font.name in ('Arial','Georgia','Times New Roman','Courier New') else 'Arial','fontSize':max(8,min(36,normal.font.size.pt if normal.font.size else 12))}}
    if images:result['images']=images
    from server.rich_document import import_rich
    rich=import_rich(document,images)
    if rich:result['rich']=rich
    result['page']['header']='\n'.join(p.text for p in section.header.paragraphs)[:500]
    result['page']['footer']='\n'.join(p.text for p in section.footer.paragraphs)[:500]
    result['page']['pageNumbers']=bool(section.footer._element.xpath('.//w:fldSimple[contains(@w:instr, "PAGE")] | .//w:instrText[contains(text(), "PAGE")]'))
    return result
