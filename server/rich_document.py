"""Validated rich-text tree. Rendering uses a fixed schema, never stored HTML."""
import re
FONTS=('Arial','Calibri','Georgia','Times New Roman','Courier New','Verdana')
NODES={'doc','text','paragraph','heading','bulletList','orderedList','listItem','taskList','taskItem','blockquote','codeBlock','horizontalRule','hardBreak','table','tableRow','tableCell','tableHeader','image','pageBreak','footnote','tableOfContents'}
MARKS={'bold','italic','underline','strike','code','link','textStyle','scriptStyle'}
def valid_rich(tree):
    count=0
    def attrs(a):
        if not isinstance(a,dict):return False
        for key,value in a.items():
            if value is None:continue
            if key in ('color','backgroundColor') and not re.fullmatch(r'#[a-fA-F0-9]{6}',str(value)):return False
            if key=='fontFamily' and value not in FONTS:return False
            if key=='fontSize' and (type(value) not in (int,float) or not 8<=value<=96):return False
            if key=='textAlign' and value not in ('left','center','right','justify'):return False
            if key=='lineHeight' and value not in (1,1.15,1.5,2,2.5,3):return False
            if key=='indent' and (type(value) is not int or not 0<=value<=8):return False
            if key=='level' and (type(value) is not int or not 1<=value<=6):return False
            if key in ('colspan','rowspan','start') and (type(value) is not int or not 1<=value<=1000):return False
            if key=='colwidth' and (not isinstance(value,list) or len(value)>100 or any(type(n) is not int or not 1<=n<=2000 for n in value)):return False
            if key=='src' and not re.fullmatch(r'drap-image:[a-zA-Z0-9_-]{1,100}',str(value)):return False
            if key=='href' and (not isinstance(value,str) or len(value)>2000 or not re.match(r'^(https?://|#[a-zA-Z0-9_-]+$)',value,re.I)):return False
            if key=='id' and (not isinstance(value,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',value)):return False
            if key in ('text','alt','title','language') and (not isinstance(value,str) or len(value)>4000):return False
            if key=='kind' and value not in ('sup','sub'):return False
            if key=='checked' and type(value) is not bool:return False
            if key=='target' and value not in ('_blank','_self'):return False
            if key=='rel' and (not isinstance(value,str) or len(value)>100):return False
            if key=='width' and (type(value) not in (int,float) or not 10<=value<=100):return False
            if key not in {'fontFamily','fontSize','color','backgroundColor','textAlign','lineHeight','indent','level','colspan','rowspan','colwidth','start','src','href','id','text','alt','title','language','kind','checked','target','rel','width'}:return False
        return True
    def walk(node,depth=0):
        nonlocal count
        count+=1
        if count>20000 or depth>30 or not isinstance(node,dict) or node.get('type') not in NODES:return False
        if set(node)-{'type','attrs','content','text','marks'} or not attrs(node.get('attrs',{})):return False
        if node['type']=='text' and (not isinstance(node.get('text'),str) or not node['text']):return False
        children=node.get('content',[]);marks=node.get('marks',[])
        if not isinstance(children,list) or not isinstance(marks,list) or len(marks)>10:return False
        if node['type']=='table':
            if not children or len(children)>500:return False
            widths=[]
            for row in children:
                if not isinstance(row,dict) or row.get('type')!='tableRow' or not isinstance(row.get('content'),list):return False
                if any(not isinstance(c,dict) or not isinstance(c.get('attrs',{}),dict) for c in row['content']):return False
                widths.append(sum(c.get('attrs',{}).get('colspan',1) if isinstance(c,dict) and isinstance(c.get('attrs',{}).get('colspan',1),int) else 100001 for c in row['content']))
            if not widths or min(widths)<0 or max(widths)>100 or max(widths)*len(children)>50000:return False
        if any(not isinstance(m,dict) or m.get('type') not in MARKS or set(m)-{'type','attrs'} or not attrs(m.get('attrs',{})) for m in marks):return False
        return all(walk(child,depth+1) for child in children)
    return isinstance(tree,dict) and tree.get('type')=='doc' and walk(tree)

def export_rich(document,tree,images):
    import io
    from docx.shared import Pt,Inches,RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.opc.part import Part
    from docx.opc.packuri import PackURI
    from lxml import etree
    from server.slides_io import image_bytes
    notes=[];headings=[]
    def gather(node):
        if node['type']=='heading':headings.append(''.join(n.get('text','') for n in node.get('content',[])))
        for child in node.get('content',[]):gather(child)
    gather(tree)
    def inline(p,node):
        kind=node['type'];a=node.get('attrs',{})
        if kind=='hardBreak':p.add_run().add_break();return
        if kind=='footnote':
            notes.append(a.get('text',''));ref=OxmlElement('w:footnoteReference');ref.set(qn('w:id'),str(len(notes)));p.add_run()._r.append(ref);return
        if kind!='text':return
        run=p.add_run(node.get('text',''))
        for mark in node.get('marks',[]):
            m=mark['type'];v=mark.get('attrs',{})
            if m=='bold':run.bold=True
            elif m=='italic':run.italic=True
            elif m=='underline':run.underline=True
            elif m=='strike':run.font.strike=True
            elif m=='code':run.font.name='Courier New'
            elif m=='scriptStyle':run.font.superscript=v.get('kind')=='sup';run.font.subscript=v.get('kind')=='sub'
            elif m=='textStyle':
                if v.get('fontFamily'):run.font.name=v['fontFamily']
                if v.get('fontSize'):run.font.size=Pt(v['fontSize'])
                if v.get('color'):run.font.color.rgb=RGBColor.from_string(v['color'][1:])
                if v.get('backgroundColor'):
                    shade=OxmlElement('w:shd');shade.set(qn('w:fill'),v['backgroundColor'][1:]);run._r.get_or_add_rPr().append(shade)
            elif m=='link':
                link=OxmlElement('w:hyperlink');url=v.get('href','')
                if url.startswith('#'):link.set(qn('w:anchor'),url[1:])
                else:link.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
                link.append(run._r);p._p.append(link)
    def block(parent,node,list_style=None):
        kind=node['type'];a=node.get('attrs',{});children=node.get('content',[])
        if kind=='table':
            width=max((sum(c.get('attrs',{}).get('colspan',1) for c in r.get('content',[])) for r in children),default=1)
            if not 1<=width<=100 or len(children)*width>50000:
                from server.store import InvalidInput
                raise InvalidInput('Tabela excede o limite de exportação.')
            table=parent.add_table(rows=len(children),cols=width);table.style='Table Grid';occupied=set()
            for r,row in enumerate(children):
                col=0
                for cell in row.get('content',[]):
                    while (r,col) in occupied:col+=1
                    ca=cell.get('attrs',{});cs=ca.get('colspan',1);rs=ca.get('rowspan',1);end_r=min(len(children)-1,r+rs-1);end_c=min(width-1,col+cs-1)
                    if col>=width:
                        from server.store import InvalidInput
                        raise InvalidInput('Estrutura de células mescladas inválida.')
                    target=table.cell(r,col)
                    if cs>1 or rs>1:target=target.merge(table.cell(end_r,end_c))
                    for rr in range(r,end_r+1):
                        for cc in range(col,end_c+1):occupied.add((rr,cc))
                    for child in cell.get('content',[]):block(target,child)
                    if len(target.paragraphs)>1 and not target.paragraphs[0].text:target._tc.remove(target.paragraphs[0]._p)
                    col+=cs
            return
        if kind=='image':
            image=images.get(a.get('src','').replace('drap-image:',''))
            if image:parent.add_paragraph().add_run().add_picture(io.BytesIO(image_bytes(image['src'])),width=Inches(6*image.get('width',80)/100))
            return
        if kind=='pageBreak':parent.add_paragraph().add_run().add_break(WD_BREAK.PAGE);return
        if kind=='tableOfContents':
            parent.add_paragraph('Sumário',style='Heading 1')
            for title in headings:parent.add_paragraph(title,style='Normal')
            return
        if kind in ('bulletList','orderedList','taskList'):
            for child in children:block(parent,child,'List Number' if kind=='orderedList' else 'List Bullet')
            return
        if kind in ('paragraph','heading','codeBlock'):
            p=parent.add_paragraph(style=('Heading '+str(a.get('level',1))) if kind=='heading' else list_style)
            if a.get('textAlign'):p.alignment={'left':WD_ALIGN_PARAGRAPH.LEFT,'center':WD_ALIGN_PARAGRAPH.CENTER,'right':WD_ALIGN_PARAGRAPH.RIGHT,'justify':WD_ALIGN_PARAGRAPH.JUSTIFY}[a['textAlign']]
            if a.get('lineHeight'):p.paragraph_format.line_spacing=a['lineHeight']
            if a.get('indent'):p.paragraph_format.left_indent=Inches(a['indent']*.3)
            for child in children:inline(p,child)
            return
        if kind=='horizontalRule':parent.add_paragraph('________________________________');return
        for child in children:block(parent,child,list_style)
    block(document,tree)
    if notes:
        root=OxmlElement('w:footnotes')
        for i,text in enumerate(notes,1):
            note=OxmlElement('w:footnote');note.set(qn('w:id'),str(i));p=OxmlElement('w:p');r=OxmlElement('w:r');t=OxmlElement('w:t');t.text=text;r.append(t);p.append(r);note.append(p);root.append(note)
        part=Part(PackURI('/word/footnotes.xml'),'application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml',etree.tostring(root),document.part.package)
        document.part.relate_to(part,RT.FOOTNOTES)

def import_rich(document,images):
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from lxml import etree
    notes={}
    for rel in document.part.rels.values():
        if rel.reltype==RT.FOOTNOTES:
            root=etree.fromstring(rel.target_part.blob,etree.XMLParser(resolve_entities=False,no_network=True))
            for note in root:
                notes[note.get(qn('w:id'))]=''.join(note.itertext())
    def run_nodes(run):
        nodes=[];marks=[]
        if run.bold:marks.append({'type':'bold'})
        if run.italic:marks.append({'type':'italic'})
        if run.underline:marks.append({'type':'underline'})
        if run.font.strike:marks.append({'type':'strike'})
        if run.font.superscript or run.font.subscript:marks.append({'type':'scriptStyle','attrs':{'kind':'sup' if run.font.superscript else 'sub'}})
        style={}
        if run.font.name in FONTS:style['fontFamily']=run.font.name
        if run.font.size:style['fontSize']=max(8,min(96,run.font.size.pt))
        try:
            if run.font.color.rgb:style['color']='#'+str(run.font.color.rgb)
        except (AttributeError,TypeError):pass
        shading=run._r.xpath('./w:rPr/w:shd')
        if shading and re.fullmatch(r'[a-fA-F0-9]{6}',shading[0].get(qn('w:fill'),'')):style['backgroundColor']='#'+shading[0].get(qn('w:fill'))
        if style:marks.append({'type':'textStyle','attrs':style})
        for i,segment in enumerate(run.text.split('\n')):
            if i:nodes.append({'type':'hardBreak'})
            if segment:nodes.append({'type':'text','text':segment,**({'marks':marks} if marks else {})})
        for ref in run._r.xpath('.//w:footnoteReference'):
            key=ref.get(qn('w:id'))
            if key in notes:nodes.append({'type':'footnote','attrs':{'id':'note-'+key,'text':notes[key][:4000]}})
        return nodes
    def paragraph(p):
        children=[]
        for part in p.iter_inner_content():
            if hasattr(part,'url'):
                for run in part.runs:
                    for node in run_nodes(run):
                        if node['type']=='text' and part.url.startswith(('http://','https://')):node.setdefault('marks',[]).append({'type':'link','attrs':{'href':part.url,'target':'_blank','rel':'noopener noreferrer'}})
                        children.append(node)
            else:children.extend(run_nodes(part))
        attrs={};kind='paragraph';name=p.style.name if p.style else ''
        if name.startswith('Heading ') and name.split()[-1].isdigit():kind='heading';attrs['level']=min(6,int(name.split()[-1]))
        if p.alignment is not None:attrs['textAlign']={0:'left',1:'center',2:'right',3:'justify'}.get(int(p.alignment),'left')
        spacing=p.paragraph_format.line_spacing
        if spacing in (1,1.15,1.5,2,2.5,3):attrs['lineHeight']=spacing
        indent=p.paragraph_format.left_indent
        if indent:attrs['indent']=max(0,min(8,round(indent.inches/.3)))
        result={'type':kind,'attrs':attrs,'content':children}
        if name.startswith('List Bullet') or name.startswith('List Number'):result={'type':'orderedList' if name.startswith('List Number') else 'bulletList','content':[{'type':'listItem','content':[result]}]}
        return result
    blocks=[];image_index=0
    for block in document.iter_inner_content():
        if hasattr(block,'rows'):
            rows=[];merged={}
            for index,row in enumerate(block.rows):
                cells=[];seen=set()
                for cell in row.cells:
                    if cell._tc in seen:continue
                    seen.add(cell._tc)
                    if cell._tc in merged:
                        merged[cell._tc]['attrs']['rowspan']+=1;continue
                    entry={'type':'tableHeader' if index==0 else 'tableCell','attrs':{'colspan':cell._tc.grid_span,'rowspan':1},'content':[paragraph(p) for p in cell.paragraphs]}
                    merged[cell._tc]=entry;cells.append(entry)
                rows.append({'type':'tableRow','content':cells})
            blocks.append({'type':'table','content':rows})
        else:
            blocks.append(paragraph(block))
            for br in block._p.xpath('.//w:br'):
                if br.get(qn('w:type'))=='page':blocks.append({'type':'pageBreak'})
            for _ in block._p.xpath('.//w:drawing//a:blip'):
                if image_index<len(images):
                    image=images[image_index];blocks.append({'type':'image','attrs':{'src':'drap-image:'+image['id'],'alt':image.get('alt',''),'width':image.get('width',80)}});image_index+=1
    result={'type':'doc','content':blocks or [{'type':'paragraph'}]}
    return result if valid_rich(result) else None


def valid_tabs(content):
    if 'tabs' not in content:return True
    tabs=content['tabs'];active=content.get('activeTab',0)
    if not isinstance(tabs,list) or not 1<=len(tabs)<=20 or type(active) is not int or not 0<=active<len(tabs):return False
    names=set()
    for tab in tabs:
        if not isinstance(tab,dict) or not isinstance(tab.get('name'),str) or not 1<=len(tab['name'])<=80 or tab['name'] in names or not isinstance(tab.get('text'),str):return False
        names.add(tab['name'])
        if 'rich' in tab and not valid_rich(tab['rich']):return False
    return tabs[active]['text']==content['text'] and tabs[active].get('rich')==content.get('rich')
