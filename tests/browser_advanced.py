"""Advanced editor controls exercised through the browser."""
import io,json,os,tempfile,threading,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from docx import Document
from server.app import handler_for
from server.store import Store

def exercise(page,base):
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    headers={'Origin':base};creds={'email':uuid.uuid4().hex+'@example.org','password':uuid.uuid4().hex+'-Test12','name':'Ana Teste'}
    assert page.request.post(base+'/api/register',headers=headers,data={**creds,'question':'pet','answer':'resposta de teste'}).ok
    assert page.request.post(base+'/api/login',headers=headers,data={**creds,'question':'pet','answer':'resposta de teste'}).ok
    items=[]
    def create(kind,title,content):
        r=page.request.post(base+'/api/items',headers=headers,data={'kind':kind,'title':title,'content':content});assert r.ok,r.text();items.append(r.json());return r.json()
    doc=create('document','Avançado Documento',{'text':'Texto especial'})
    create('slides','Avançado Slides',{'slides':[{'title':'Público','body':'Visível','notes':'SEGREDO PRIVADO','objects':[{'id':str(i),'type':'rect','x':i*30+5,'y':50,'w':10,'h':10,'text':str(i)} for i in range(2)]},{'title':'Conclusão','body':'Fim','notes':''}]})
    create('sheet','Avançado Planilha',{'cells':[['X','Y'],['1','10'],['2','20'],['3','30']]})
    def open_item(title):
        page.get_by_role('button',name='Todos os arquivos',exact=False).click();page.locator('[data-open]').filter(has_text=title).click()
    page.goto(base);page.locator('[data-open]').filter(has_text='Avançado Documento').click();expect(page.locator('#preview')).to_have_attribute('data-ready','true')
    visual=page.get_by_role('textbox',name='Página do documento',exact=True);visual.focus();visual.press('Control+A');page.locator('#rich-font').select_option('Georgia');page.locator('#rich-size').select_option('24');page.locator('[data-rich-command="underline"]').click();page.locator('#rich-color').fill('#123456');page.locator('#rich-color').dispatch_event('change');expect(visual.locator('u')).to_contain_text('Texto especial');expect(visual.locator('span').first).to_have_css('font-family','Georgia')
    visual.press('Control+End');page.locator('#rich-note').click();page.locator('#footnote-form textarea').fill('Referência importante');page.get_by_role('button',name='Inserir nota',exact=True).click();expect(page.locator('.document-notes')).to_contain_text('Referência importante')
    page.locator('#rich-header').click();page.locator('[name="header"]').fill('Empresa DRAP');page.locator('[name="footer"]').fill('Confidencial');page.locator('[name="pageNumbers"]').check();page.get_by_role('button',name='Aplicar cabeçalho',exact=True).click()
    page.locator('#doc-tab-add').click();expect(page.locator('#preview')).to_have_attribute('data-ready','true');visual.fill('Texto da segunda aba');page.locator('[data-doc-tab="0"]').click();expect(page.locator('#preview')).to_have_attribute('data-ready','true');expect(visual.locator('u')).to_contain_text('Texto especial')
    page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão');page.reload();page.locator('[data-open]').filter(has_text='Avançado Documento').click();expect(page.locator('#preview')).to_have_attribute('data-ready','true');expect(visual.locator('u')).to_contain_text('Texto especial');expect(page.locator('.document-notes')).to_contain_text('Referência importante')
    with page.expect_download() as dl:page.get_by_role('button',name='Baixar DOCX',exact=True).click()
    result=Document(io.BytesIO(Path(dl.value.path()).read_bytes()));assert any('Texto da segunda aba' in p.text for p in result.paragraphs);assert result.sections[0].header.paragraphs[0].text=='Empresa DRAP'
    open_item('Avançado Slides');page.locator('#slide-multiple').select_option(['0','1']);page.locator('#slide-group').click();page.locator('#object-rotation').fill('25');page.locator('#object-rotation').dispatch_event('change');page.locator('[data-object="0"]').press('ArrowRight');expect(page.locator('#object-x')).to_have_value('6');page.locator('#slide-object-list').select_option('1');expect(page.locator('#object-x')).to_have_value('36')
    with page.expect_popup() as popup:page.locator('#present-separate').click()
    audience=popup.value;expect(audience.locator('#audience-stage')).to_contain_text('Público');expect(audience.locator('body')).not_to_contain_text('SEGREDO PRIVADO');expect(page.locator('#speaker-notes')).to_contain_text('SEGREDO PRIVADO');page.locator('#speaker-forward').click();expect(audience.locator('#audience-stage')).to_contain_text('Conclusão');page.locator('#speaker-exit').click();page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    open_item('Avançado Planilha');expect(page.locator('#spreadsheet')).to_have_attribute('data-ready','true');page.locator('#sheet-address').fill('A1:B4');page.locator('#sheet-chart-add').click();page.locator('#chart-form [name="type"]').select_option('radar');page.get_by_role('button',name='Adicionar gráfico',exact=True).click();expect(page.locator('svg[aria-label="Avançado Planilha"]')).to_be_visible();page.locator('#sheet-protect').click();page.locator('#protect-form [name="range"]').fill('B2:B4');page.get_by_role('button',name='Proteger intervalo',exact=True).click();expect(page.locator('#sheet-protected-summary')).to_contain_text('1 intervalos');page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    create('board','Avançado Projeto',{'tasks':[{'id':'a','title':'Planejar','start':'2026-11-01','due':'2026-11-02','status':'A fazer'},{'id':'b','title':'Publicar','start':'2026-11-03','due':'2026-11-04','status':'A fazer','dependsOn':['a']}]})
    create('calendar','Avançado Agenda',{'events':[{'title':'Reunião mensal','start':__import__('datetime').date.today().strftime('%Y-%m-10T10:00:00Z'),'end':__import__('datetime').date.today().strftime('%Y-%m-10T11:00:00Z')}]})
    create('form','Avançado Quiz',{'questions':['Capital?'],'fields':[{'type':'choice','required':True,'options':['Brasília','Recife']}],'responses':[]})
    page.reload();open_item('Avançado Projeto');expect(page.locator('.board')).to_contain_text('Depende de: Planejar');page.locator('[data-task="1"]').select_option('Em andamento');expect(page.get_by_role('status')).to_contain_text('Conclua');expect(page.locator('[data-task="1"]')).to_have_value('A fazer');page.locator('[data-task="0"]').select_option('Concluído');page.locator('[data-task="1"]').select_option('Em andamento');page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    open_item('Avançado Agenda');expect(page.locator('.month-grid')).to_be_visible();page.locator('#month-today').click();expect(page.locator('[data-month-event="0"]')).to_contain_text('Reunião mensal');page.locator('[data-month-event="0"]').click();expect(page.locator('#edit-event')).to_be_visible();page.get_by_role('button',name='Aplicar compromisso',exact=True).click();page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    open_item('Avançado Quiz');page.locator('#form-quiz').check();page.locator('[data-correct="0"]').select_option('Brasília');page.locator('[data-points="0"]').fill('5');page.locator('[data-points="0"]').dispatch_event('change');page.locator('[name="q0"]').select_option('Brasília');page.get_by_role('button',name='Registrar resposta',exact=True).click();expect(page.get_by_text('Nota: 5 de 5',exact=True)).to_be_visible();page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    assert not errors,errors
    for item in items:
        current=page.request.get(base+'/api/items/'+item['id']).json();r=page.request.post(base+'/api/items/'+item['id'],headers=headers,data={'title':current['title'],'content':current['content'],'version':current['version'],'deleted':True});assert r.ok,r.text()
    page.request.post(base+'/api/logout',headers=headers,data={})
    print('PASS: rich formatting, tabs, notes, DOCX, grouped slide movement, separate presenter, charts, protection, projects, calendar and quizzes',flush=True)

def main():
    expect.set_options(timeout=30000)
    with tempfile.TemporaryDirectory() as tmp:
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(tmp)/'test.sqlite')));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(30000);exercise(page,f'http://127.0.0.1:{server.server_port}');browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
