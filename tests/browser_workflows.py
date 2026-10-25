"""Regression journeys for document, calendar, forms, records, board and read-only navigation."""
import io,os,tempfile,threading,uuid,json
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from PIL import Image
from docx import Document
from server.app import handler_for
from server.store import Store

def exercise(page,base,title='Fluxos integrados'):
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base);page.get_by_role('button',name='Criar minha conta').click();page.get_by_label('Nome',exact=True).fill('Ana Teste');page.get_by_label('E-mail',exact=True).fill(uuid.uuid4().hex+'@example.org');page.get_by_label('Senha',exact=True).fill(uuid.uuid4().hex+'-Teste12');page.get_by_role('button',name='Criar conta',exact=False).click();expect(page.get_by_role('heading',name='Olá, Ana. Vamos criar?')).to_be_visible()
    def create(kind,name):
        page.get_by_role('button',name='Todos os arquivos',exact=False).click();page.get_by_role('button',name='＋ Criar novo').click();page.locator('#create-form select').select_option(kind);page.get_by_label('Nome do arquivo',exact=True).last.fill(name);page.get_by_role('button',name='Criar arquivo',exact=True).click();expect(page.locator('#title')).to_have_value(name)
    def save():page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    def get(name):return next(x for x in page.request.get(base+'/api/items').json()['items'] if x['title']==name)
    create('document',title)
    if page.get_by_role('button',name='Editar Markdown',exact=True).is_visible():page.get_by_role('button',name='Editar Markdown',exact=True).click()
    page.locator('#text').fill('# Plano\n\n| Nome | Valor |\n| --- | --- |\n| Ana | 10 |\n\n- Tarefa\n[Site](https://example.org)\n')
    out=io.BytesIO();Image.new('RGB',(160,90),'green').save(out,format='PNG')
    with page.expect_file_chooser() as chooser:page.get_by_role('button',name='Inserir imagem',exact=True).click()
    chooser.value.set_files({'name':'foto.png','mimeType':'image/png','buffer':out.getvalue()});expect(page.locator('#preview img')).to_be_visible()
    page.get_by_role('button',name='Gerenciar imagens',exact=True).click();page.get_by_label('Descrição da imagem 1',exact=True).fill('Foto do plano');page.get_by_label('Largura da imagem 1',exact=True).fill('60');page.get_by_label('Largura da imagem 1',exact=True).press('Tab');page.get_by_role('button',name='Concluir',exact=True).click();save();page.reload();page.get_by_role('button',name=title,exact=False).click();expect(page.locator('#preview img')).to_have_attribute('alt','Foto do plano')
    with page.expect_download() as dl:page.get_by_role('button',name='Baixar DOCX',exact=True).click()
    data=Path(dl.value.path()).read_bytes();doc=Document(io.BytesIO(data));assert len(doc.tables)==1 and len(doc.inline_shapes)==1
    with page.expect_download() as html:page.get_by_role('button',name='Baixar HTML com imagens',exact=True).click()
    assert 'data:image/png;base64,' in Path(html.value.path()).read_text()
    document=get(title)
    page.get_by_role('button',name='Criar apresentação ↗',exact=True).click();expect(page.locator('#slide-preview img')).to_be_visible()
    create('calendar','Agenda revisada');page.get_by_label('Título do evento',exact=True).fill('Reunião');page.get_by_label('Data e hora de início',exact=True).fill('2026-11-12T10:00');page.get_by_label('Data e hora de fim',exact=True).fill('2026-11-12T11:00');page.get_by_role('button',name='＋ Adicionar',exact=True).click();page.get_by_role('button',name='Editar compromisso',exact=True).click();page.get_by_label('Título do compromisso',exact=True).fill('Reunião remarcada');page.get_by_label('Início',exact=True).fill('2026-11-13T14:00');page.get_by_label('Fim',exact=True).fill('2026-11-13T15:00');page.get_by_label('Descrição do compromisso',exact=True).fill('Revisar orçamento');page.get_by_role('button',name='Aplicar compromisso',exact=True).click();save();expect(page.get_by_role('heading',name='Reunião remarcada',exact=True)).to_be_visible()
    with page.expect_download() as dl:page.get_by_role('button',name='Baixar ICS',exact=True).click()
    assert 'Revisar orçamento' in Path(dl.value.path()).read_text()
    create('form','Pesquisa revisada');page.locator('[data-question="0"]').fill('Nome');page.locator('[data-field-required="0"]').uncheck();expect(page.locator('[name="q0"]')).not_to_have_attribute('required','');page.get_by_role('button',name='＋ Pergunta de texto',exact=True).click();page.locator('[data-question="1"]').fill('Nome');page.locator('[name="q0"]').fill('Ana');page.locator('[name="q1"]').fill('Bia');page.get_by_role('button',name='Registrar resposta',exact=True).click();save()
    with page.expect_download() as dl:page.get_by_role('button',name='Baixar respostas CSV',exact=True).click()
    csv=Path(dl.value.path()).read_text();assert 'Ana' in csv and 'Bia' in csv
    page.get_by_role('button',name='Respostas → Tabela',exact=True).click();expect(page.locator('[data-table-r="0"][data-table-c="1"]')).to_have_value('Ana');expect(page.locator('[data-table-r="0"][data-table-c="2"]')).to_have_value('Bia')
    create('table','Registros revisados')
    csv='Nome,Quantidade\n'+ '\n'.join(('=1+1' if i==0 else 'Registro '+str(i))+','+str(i) for i in range(200))
    with page.expect_file_chooser() as chooser:page.get_by_role('button',name='Importar CSV',exact=True).click()
    chooser.value.set_files({'name':'registros.csv','mimeType':'text/csv','buffer':csv.encode()});expect(page.locator('[data-table-row]')).to_have_count(200);page.locator('[data-column-type="1"]').select_option('number');page.get_by_label('Filtrar registros',exact=True).fill('Registro 199');page.locator('[data-sort-column="1"]').click();page.locator('[data-sort-column="1"]').click();expect(page.get_by_label('Filtrar registros',exact=True)).to_have_value('Registro 199');expect(page.locator('[data-table-row]:visible')).to_have_count(1);save()
    page.get_by_role('button',name='Abrir como planilha ↗',exact=True).click();expect(page.locator('#spreadsheet')).to_have_attribute('data-ready','true');converted=get('Registros revisados — Planilha');cells=converted['content']['workbook']['sheets']['records']['cellData'];assert len(cells)==201;assert cells['200']['0']=={'v':'=1+1','t':1};assert cells['1']['1']['v']==199
    create('board','Tarefas revisadas');page.get_by_label('Nome da tarefa',exact=True).fill('Publicar');page.get_by_role('button',name='＋ Adicionar tarefa',exact=True).click();page.get_by_role('button',name='Detalhes',exact=True).last.click();page.get_by_label('Responsável',exact=True).fill('Ana');page.locator('[name="subtasks"]').fill('Revisar\nAprovar');page.get_by_role('button',name='Aplicar detalhes',exact=True).click();page.get_by_label('Revisar',exact=True).check();save();assert get('Tarefas revisadas')['content']['tasks'][-1]['subtasks'][0]['done']
    create('diagram','Diagrama revisado');node=page.locator('[data-drag-node="0"]');node.focus()
    for _ in range(13):page.keyboard.press('Shift+ArrowDown')
    assert float(page.locator('#flow-canvas').get_attribute('viewBox').split()[-1])>600
    save();diagram=get('Diagrama revisado')
    create('portal','Portal revisado');page.get_by_label('Arquivo para vincular',exact=True).select_option(document['id']);page.get_by_role('button',name='Vincular arquivo',exact=True).click();save();portal=get('Portal revisado')
    ctx=page.context.browser.new_context();reader=ctx.new_page();creds={'email':uuid.uuid4().hex+'@example.org','password':uuid.uuid4().hex+'-Leitor12'};headers={'Origin':base};assert reader.request.post(base+'/api/register',headers=headers,data={**creds,'name':'Leitor'}).ok;assert reader.request.post(base+'/api/login',headers=headers,data=creds).ok
    for item in [document,portal,diagram]:assert page.request.post(base+'/api/items/'+item['id']+'/share',headers=headers,data={'email':creds['email'],'role':'read'}).ok
    reader.goto(base);reader.get_by_role('button',name='Portal revisado',exact=False).click();expect(reader.locator('[data-link]')).to_be_enabled();reader.locator('[data-link]').click();expect(reader.locator('#export-text')).to_be_enabled();expect(reader.locator('#document-image')).to_be_disabled();expect(reader.locator('#preview img')).to_be_visible()
    reader.get_by_role('button',name='Todos os arquivos',exact=False).click();reader.get_by_role('button',name='Diagrama revisado',exact=False).click()
    with reader.expect_download() as svg:reader.get_by_role('button',name='Baixar SVG',exact=True).click()
    assert '<svg' in Path(svg.value.path()).read_text()
    for item in [document,portal,diagram]:assert page.request.post(base+'/api/items/'+item['id']+'/share',headers=headers,data={'email':creds['email'],'role':'remove'}).ok
    reader.request.post(base+'/api/logout',headers=headers,data={});ctx.close()
    assert not errors,errors
    print('PASS: imagens/DOCX/HTML, documento→slides, edição de agenda/ICS, perguntas repetidas, CSV/200 registros→planilha, tarefas, diagrama e links/exportações em leitura',flush=True)
    return document

def main():
    expect.set_options(timeout=20000)
    with tempfile.TemporaryDirectory() as tmp:
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(tmp)/'test.sqlite')));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(20000);exercise(page,f'http://127.0.0.1:{server.server_port}');browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
