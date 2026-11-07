"""User-visible tools: saved settings, safe sheet transformations and slide playback."""
import io,os,tempfile,threading,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from docx import Document
from pptx import Presentation
from server.app import handler_for
from server.store import Store

def exercise(page,base):
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    headers={'Origin':base};creds={'email':uuid.uuid4().hex+'@example.org','password':uuid.uuid4().hex+'-Test12','name':'Ana Teste'}
    assert page.request.post(base+'/api/register',headers=headers,data={**creds,'question':'pet','answer':'resposta de teste'}).ok
    assert page.request.post(base+'/api/login',headers=headers,data={**creds,'question':'pet','answer':'resposta de teste'}).ok
    def create(kind,title,content):
        response=page.request.post(base+'/api/items',headers=headers,data={'kind':kind,'title':title,'content':content});assert response.ok,response.text();return response.json()
    doc=create('document','Google Documento',{'text':'# Relatório\n\nTexto de exemplo\n\n## Metas\n\nMais conteúdo'})
    sheet=create('sheet','Google Planilha',{'cells':[['Nome','Valor'],[' Ana  Silva ','10'],[' Ana  Silva ','10'],['Bruno','20'],[' =1+2 ','']]})
    deck=create('slides','Google Slides',{'slides':[{'title':'Abertura','body':'Primeiro','notes':'Anotações privadas','objects':[{'id':str(i),'type':'rect','x':i*30+5,'y':50,'w':10,'h':10,'text':str(i)} for i in range(3)]},{'title':'Pular','body':'Oculto','notes':''},{'title':'Fim','body':'Último','notes':'Conclusão'}]})
    page.goto(base);page.locator('[data-open]').filter(has_text='Google Documento').click();expect(page.locator('#preview')).to_have_attribute('data-ready','true')
    page.locator('#document-outline').click();expect(page.get_by_role('complementary',name='Estrutura do documento').get_by_role('button')).to_have_count(2);page.locator('[data-outline="1"]').click()
    page.locator('#document-statistics').click();expect(page.locator('dialog')).to_contain_text('Caracteres sem espaços');page.locator('#statistics-close').click()
    page.locator('#document-page').click();page.locator('[name="orientation"]').select_option('landscape');page.locator('[name="margin"]').fill('15');page.locator('[name="font"]').select_option('Georgia');page.locator('[name="fontSize"]').fill('14');page.locator('[name="align"]').select_option('justify');page.get_by_role('button',name='Aplicar configuração').click()
    page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão');page.reload();page.locator('[data-open]').filter(has_text='Google Documento').click();expect(page.locator('#preview')).to_have_attribute('data-ready','true');expect(page.locator('#preview')).to_have_css('font-family','Georgia')
    with page.expect_download() as dl:page.get_by_role('button',name='Baixar DOCX',exact=True).click()
    d=Document(io.BytesIO(Path(dl.value.path()).read_bytes()));assert d.sections[0].page_width>d.sections[0].page_height;assert d.styles['Normal'].font.name=='Georgia'
    page.get_by_role('button',name='Todos os arquivos',exact=False).click();page.locator('[data-open]').filter(has_text='Google Planilha').click();expect(page.locator('#spreadsheet')).to_have_attribute('data-ready','true')
    page.locator('#sheet-address').fill('A1:B5');page.locator('#sheet-transform').click();page.locator('[name="operation"]').select_option('trim');page.locator('[name="target"]').fill('A1');page.get_by_role('button',name='Criar resultado',exact=True).click();expect(page.locator('#transform-error')).to_contain_text('contém dados');page.locator('[name="target"]').fill('D1');page.get_by_role('button',name='Criar resultado',exact=True).click();expect(page.locator('dialog')).not_to_be_visible()
    page.locator('#sheet-address').fill('D2');page.locator('#sheet-select').click();expect(page.locator('#sheet-value')).to_have_value('Ana Silva')
    page.locator('#sheet-address').fill('D5');page.locator('#sheet-select').click();expect(page.locator('#sheet-value')).to_have_value('=1+2')
    page.locator('#sheet-address').fill('D1:E4');page.locator('#sheet-transform').click();page.locator('[name="operation"]').select_option('unique');page.locator('[name="header"]').check();page.locator('[name="target"]').fill('G1');page.get_by_role('button',name='Criar resultado',exact=True).click();expect(page.locator('dialog')).not_to_be_visible()
    page.locator('#sheet-address').fill('G3');page.locator('#sheet-select').click();expect(page.locator('#sheet-value')).to_have_value('Bruno')
    page.locator('#sheet-stats').click();expect(page.locator('dialog')).to_contain_text('Células preenchidas');page.locator('#stats-close').click()
    page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão');page.reload();page.locator('[data-open]').filter(has_text='Google Planilha').click();expect(page.locator('#spreadsheet')).to_have_attribute('data-ready','true');page.locator('#sheet-address').fill('G3');page.locator('#sheet-select').click();expect(page.locator('#sheet-value')).to_have_value('Bruno')
    page.locator('#sheet-address').fill('D5');page.locator('#sheet-select').click();expect(page.locator('#sheet-value')).to_have_value('=1+2')
    page.get_by_role('button',name='Todos os arquivos',exact=False).click();page.locator('[data-open]').filter(has_text='Google Slides').click();page.locator('#slide-background').fill('#123456');page.locator('#slide-background').dispatch_event('change');page.locator('#slide-foreground').fill('#ffffff');page.locator('#slide-foreground').dispatch_event('change');page.locator('#slide-transition').select_option('fade')
    page.locator('#slide-object-list').select_option('0');page.locator('#object-position').select_option('center');expect(page.locator('#object-x')).to_have_value('45');page.locator('#slide-undo').click();page.locator('#slide-object-list').select_option('0');page.locator('#object-distribute-x').click()
    page.locator('[data-slide="1"]').click();page.locator('#slide-hidden').check();page.locator('#present').click();expect(page.locator('.present')).to_contain_text('1 / 2');page.locator('#present-notes').click();expect(page.locator('.present-notes')).to_contain_text('Anotações privadas');page.locator('#next-slide').click();expect(page.locator('.present .slide-heading')).to_have_text('Fim');page.keyboard.press('b');expect(page.locator('.present .slide-stage')).to_have_class(__import__('re').compile('present-black'));page.keyboard.press('Escape')
    page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    with page.expect_download() as dl:page.get_by_role('button',name='Baixar PPTX',exact=True).click()
    p=Presentation(io.BytesIO(Path(dl.value.path()).read_bytes()));assert p.slides[1]._element.get('show')=='0';assert p.slides[0]._element.xpath('./p:transition/p:fade');assert str(p.slides[0].background.fill.fore_color.rgb)=='123456'
    page.reload();page.locator('[data-open]').filter(has_text='Google Slides').click();expect(page.locator('#slide-background')).to_have_value('#123456');page.locator('[data-slide="1"]').click();expect(page.locator('#slide-hidden')).to_be_checked()
    page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2');page.screenshot(path='/tmp/drap-google-tools.png',full_page=True)
    assert not errors,errors
    print('PASS: estrutura, estatísticas, página, DOCX, transformação protegida, persistência, alinhamento, fundo, ocultar, transição, notas e PPTX',flush=True)

def main():
    expect.set_options(timeout=20000)
    with tempfile.TemporaryDirectory() as tmp:
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(tmp)/'test.sqlite')));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(20000);exercise(page,f'http://127.0.0.1:{server.server_port}');browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
