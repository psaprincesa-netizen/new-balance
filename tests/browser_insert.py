"""Auxiliary Insert menu: real files, content insertion and access permissions."""
import base64,io,os,tempfile,threading,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from docx import Document
from PIL import Image
from server.app import handler_for
from server.store import Store

def exercise(page,base):
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    headers={'Origin':base};creds={'email':uuid.uuid4().hex+'@example.org','password':uuid.uuid4().hex+'-Test12','name':'Ana Teste'}
    assert page.request.post(base+'/api/register',headers=headers,data={**creds,'question':'pet','answer':'resposta de teste'}).ok;assert page.request.post(base+'/api/login',headers=headers,data={**creds,'question':'pet','answer':'resposta de teste'}).ok
    def create(kind,title,content):
        r=page.request.post(base+'/api/items',headers=headers,data={'kind':kind,'title':title,'content':content});assert r.ok,r.text();return r.json()
    item=create('document','Inserção de arquivos',{'text':'Texto original'});source=create('document','Documento privado de origem',{'text':'# Da biblioteca\nConteúdo copiado'})
    sheet=create('sheet','Anexo em planilha',{'cells':[['1','2']]})
    deck=create('slides','Anexo em slides',{'slides':[{'title':'Slide','body':'','notes':''}]})
    page.goto(base);page.get_by_role('button',name='Inserção de arquivos',exact=False).click();expect(page.locator('#preview')).to_have_attribute('data-ready','true')
    visual=page.get_by_role('textbox',name='Página do documento',exact=True)
    def insert_file(button,name,mime,data):
        page.locator('#aux-insert').click()
        with page.expect_file_chooser() as chooser:page.locator(button).click()
        chooser.value.set_files({'name':name,'mimeType':mime,'buffer':data})
    visual.focus();visual.press('Control+End')
    image=io.BytesIO();Image.new('RGB',(90,50),'green').save(image,format='PNG')
    doc=Document();doc.add_heading('Documento inserido',level=1);doc.add_paragraph('Texto com imagem');doc.add_picture(io.BytesIO(image.getvalue()));out=io.BytesIO();doc.save(out)
    insert_file('#insert-document-file','Entrada.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document',out.getvalue())
    page.locator('#insert-document-done').click();expect(visual).to_contain_text('Texto original');expect(visual).to_contain_text('Documento inserido');expect(visual.locator('img')).to_have_count(1)
    visual.focus();visual.press('Control+End');insert_file('#insert-document-file','Literal.txt','text/plain','**literal** e [texto](https://example.org)'.encode());expect(visual).to_contain_text('**literal**');expect(visual.locator('strong')).to_have_count(0)
    raw=b'%PDF-1.7\n\x00\xffDRAP attachment'
    insert_file('#insert-attachment','proposta.pdf','application/pdf',raw);expect(page.locator('#inserted-content')).to_contain_text('proposta.pdf')
    insert_file('#insert-attachment','grande.zip','application/zip',b'x'*1000001);expect(page.get_by_role('status')).to_contain_text('no máximo 1 MB');expect(page.locator('.attachment-card')).to_have_count(1)
    page.locator('#aux-insert').click();page.locator('#insert-library').click();page.locator('#insert-library-item').select_option(source['id']);page.get_by_role('button',name='Inserir selecionado',exact=True).click();expect(page.locator('.attachment-card')).to_have_count(2)
    page.locator('#aux-insert').click();page.locator('#insert-menu-link').click();page.get_by_label('Nome',exact=True).fill('Referência');page.get_by_label('Endereço',exact=True).fill('https://example.org/referencia');page.get_by_role('button',name='Adicionar link',exact=True).click();expect(page.locator('#inserted-content a')).to_have_attribute('href','https://example.org/referencia')
    page.locator('#aux-insert').click();page.locator('#insert-library').click();page.locator('#insert-library-item').select_option(source['id']);page.locator('[name="mode"]').select_option('content');page.get_by_role('button',name='Inserir selecionado',exact=True).click();expect(visual).to_contain_text('Conteúdo copiado')
    page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão');page.reload();page.get_by_role('button',name='Inserção de arquivos',exact=False).click();expect(page.locator('#preview')).to_have_attribute('data-ready','true');expect(visual).to_contain_text('Texto original');expect(visual.locator('img')).to_have_count(1);expect(page.locator('.attachment-card')).to_have_count(3)
    with page.expect_download() as dl:page.locator('[data-attachment-open="0"]').click()
    assert Path(dl.value.path()).read_bytes()==raw;assert dl.value.suggested_filename=='proposta.pdf'
    saved=page.request.get(base+'/api/items/'+item['id']).json();assert base64.b64decode(saved['content']['attachments'][0]['data'])==raw
    with page.expect_download() as dl:page.get_by_role('button',name='Baixar DOCX',exact=True).click()
    exported=Document(io.BytesIO(Path(dl.value.path()).read_bytes()));assert len(exported.inline_shapes)==1;assert 'Texto original' in '\n'.join(p.text for p in exported.paragraphs)
    # Reader can download attachments but cannot insert; linking the source does not grant access.
    ctx=page.context.browser.new_context();reader=ctx.new_page();reader_creds={'name':'Leitor','email':uuid.uuid4().hex+'@example.org','password':uuid.uuid4().hex+'-Read12'}
    assert reader.request.post(base+'/api/register',headers=headers,data={**reader_creds,'question':'pet','answer':'resposta de teste'}).ok;assert reader.request.post(base+'/api/login',headers=headers,data={**reader_creds,'question':'pet','answer':'resposta de teste'}).ok
    assert page.request.post(base+'/api/items/'+item['id']+'/share',headers=headers,data={'email':reader_creds['email'],'role':'read'}).ok
    reader.goto(base);reader.get_by_role('button',name='Inserção de arquivos',exact=False).click();expect(reader.locator('#aux-insert')).to_be_disabled();expect(reader.locator('[data-attachment-remove]')).to_have_count(0)
    with reader.expect_download() as dl:reader.locator('[data-attachment-open="0"]').click()
    assert Path(dl.value.path()).read_bytes()==raw
    reader.locator('[data-attachment-open="1"]').click();expect(reader.get_by_role('status')).to_contain_text('Arquivo não encontrado');assert reader.request.get(base+'/api/items/'+source['id']).status==404
    assert reader.request.post(base+'/api/items/'+item['id'],headers=headers,data=saved).status==403
    assert page.request.post(base+'/api/items/'+item['id']+'/share',headers=headers,data={'email':reader_creds['email'],'role':'remove'}).ok;assert reader.request.get(base+'/api/items/'+item['id']).status==404;ctx.close()
    page.locator('[data-attachment-remove="2"]').click();expect(page.locator('.attachment-card')).to_have_count(2);page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    page.set_viewport_size({'width':390,'height':844});page.locator('#aux-insert').click();expect(page.locator('#insert-attachment')).to_be_visible();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');page.screenshot(path='/tmp/drap-insert-menu.png',full_page=True);page.locator('#insert-close').click();page.set_viewport_size({'width':1600,'height':1100})
    # The same button works on a spreadsheet and survives saving its native editor.
    page.get_by_role('button',name='Todos os arquivos',exact=False).click();page.get_by_role('button',name='Anexo em planilha',exact=False).click();expect(page.locator('#spreadsheet')).to_have_attribute('data-ready','true')
    insert_file('#insert-attachment','dados.bin','application/octet-stream',b'\x01\x02');page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão');insert_file('#insert-attachment','segundo.bin','application/octet-stream',b'\x03');expect(page.locator('.attachment-card')).to_have_count(2);page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    assert len(page.request.get(base+'/api/items/'+sheet['id']).json()['content']['attachments'])==2
    page.get_by_role('button',name='Todos os arquivos',exact=False).click();page.get_by_role('button',name='Anexo em slides',exact=False).click();page.locator('#slide-rect').click()
    insert_file('#insert-attachment','apoio.bin','application/octet-stream',b'apoio');expect(page.locator('.attachment-card')).to_have_count(1);page.locator('#slide-undo').click();page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    restored=page.request.get(base+'/api/items/'+deck['id']).json()['content'];assert len(restored['attachments'])==1;assert not restored['slides'][0].get('objects')
    assert not errors,errors
    print('PASS: menu Inserir, DOCX/imagem, TXT literal, biblioteca, anexos binários, limites, download, persistência, leitura/revogação, celular, planilha e desfazer nos slides',flush=True)

def main():
    expect.set_options(timeout=20000)
    with tempfile.TemporaryDirectory() as tmp:
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(tmp)/'test.sqlite')));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(20000);
                try:exercise(page,f'http://127.0.0.1:{server.server_port}')
                except Exception:
                    print('STATUS:',page.get_by_role('status').all_text_contents(),flush=True);print('DIALOG:',page.locator('dialog').all_text_contents(),flush=True);page.screenshot(path='/tmp/drap-insert-failure.png',full_page=True);raise
                finally:browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
