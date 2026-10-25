"""Real pivot editor journeys: configuration, refresh, drill-down and recovery."""
import io,json,os,tempfile,threading,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.app import handler_for
from server.store import Store

def exercise(page,base,title='Receitas dinâmicas'):
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base);page.get_by_role('button',name='Criar minha conta').click()
    page.get_by_label('Nome',exact=True).fill('Ana Teste');page.get_by_label('E-mail',exact=True).fill(uuid.uuid4().hex+'@example.org');page.get_by_label('Senha',exact=True).fill(uuid.uuid4().hex+'-Teste12')
    page.get_by_role('button',name='Criar conta',exact=False).click();expect(page.get_by_role('heading',name='Olá, Ana. Vamos criar?')).to_be_visible()
    page.get_by_role('button',name='＋ Criar novo').click();page.locator('#create-form select').select_option('sheet');page.get_by_label('Nome do arquivo',exact=True).last.fill(title);page.get_by_role('button',name='Criar arquivo',exact=True).click()
    def ready():expect(page.locator('#spreadsheet')).to_have_attribute('data-ready','true')
    def save():
        page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão');ready()
    ready()
    csv='Equipe,Mês,Receita\nA,Jan,10\nA,Jan,30\nA,Fev,-5\nB,Jan,20\nB,Fev,\nB,Fev,texto'
    with page.expect_file_chooser() as chooser:page.get_by_role('button',name='Importar CSV',exact=True).click()
    chooser.value.set_files({'name':'receitas.csv','mimeType':'text/csv','buffer':csv.encode()})
    page.locator('#sheet-address').fill('A1');page.locator('#sheet-select').click();expect(page.locator('#sheet-value')).to_have_value('Equipe')
    # Currency formatting must not turn numeric source data into display text
    # (e.g. "R$10,00") when the pivot reads the range.
    page.set_viewport_size({'width':1920,'height':1100})
    page.locator('#sheet-address').fill('C2:C7');page.locator('#sheet-select').click()
    page.locator('[data-u-command="sheet.command.numfmt.set.currency"]:visible').click()
    page.set_viewport_size({'width':1600,'height':1100})
    page.locator('#sheet-address').fill('A1:C7');page.get_by_role('button',name='Tabela dinâmica',exact=True).click()
    page.get_by_label('Título do resumo',exact=True).fill('Receita por equipe e mês')
    page.get_by_label('Agrupar linhas por',exact=True).select_option('0');page.get_by_label('Agrupar colunas por',exact=True).select_option('1');page.get_by_label('Campo de valores',exact=True).select_option('2');page.get_by_label('Cálculo',exact=True).select_option('avg')
    page.get_by_role('button',name='Salvar tabela dinâmica',exact=True).click();expect(page.locator('dialog')).not_to_be_visible()
    pivot=page.locator('#sheet-pivots');expect(pivot.get_by_role('button',name='Registros de Total geral, Total geral',exact=True)).to_have_text('13.75')
    pivot.get_by_role('button',name='Registros de A, Jan',exact=True).click();expect(page.locator('dialog')).to_contain_text('2 registros.')
    with page.expect_download() as details:page.get_by_role('button',name='Baixar todos os registros CSV',exact=True).click()
    assert '"10"' in Path(details.value.path()).read_text() and '"30"' in Path(details.value.path()).read_text()
    page.get_by_role('button',name='Fechar',exact=True).click()
    pivot.get_by_role('button',name='Configurar resumo',exact=True).click();page.get_by_label('Cálculo',exact=True).select_option('sum');page.get_by_label('Filtrar campo',exact=True).select_option('0');page.get_by_label('Valor do filtro',exact=True).fill('B');page.get_by_role('button',name='Salvar tabela dinâmica',exact=True).click();expect(page.locator('dialog')).not_to_be_visible()
    expect(pivot.get_by_role('button',name='Registros de B, Total geral',exact=True)).to_have_text('20')
    page.locator('#sheet-address').fill('C5');page.locator('#sheet-value').fill('=20*2');page.locator('#sheet-apply').click()
    expect(pivot.get_by_role('button',name='Registros de B, Total geral',exact=True)).to_have_text('40')
    save();page.reload();page.get_by_role('button',name=title,exact=False).click();ready()
    expect(pivot.get_by_role('button',name='Registros de B, Total geral',exact=True)).to_have_text('40')
    item=next(x for x in page.request.get(base+'/api/items').json()['items'] if x['title']==title)
    assert item['content']['pivots'][0]['filterValue']=='B'
    with page.expect_download() as result:page.get_by_role('button',name='Baixar XLSX',exact=True).click()
    from openpyxl import load_workbook
    book=load_workbook(io.BytesIO(Path(result.value.path()).read_bytes()));assert list(book['Resumo 1'].values)==[('Equipe','Jan','Fev','Total geral'),('B',40,0,40),('Total geral',40,0,40)]
    with page.expect_download() as backup:page.get_by_role('button',name='Exportar JSON',exact=True).click()
    data=json.loads(Path(backup.value.path()).read_text());data['items'][0]['title']='Cópia '+title
    with page.expect_file_chooser() as chooser:page.get_by_role('button',name='Importar JSON',exact=True).click()
    chooser.value.set_files({'name':'copia.json','mimeType':'application/json','buffer':json.dumps(data).encode()});expect(page.get_by_role('status')).to_contain_text('1 arquivos importados')
    page.get_by_role('button',name='Todos os arquivos',exact=False).click();page.get_by_role('button',name='Cópia '+title,exact=False).click();ready();expect(pivot.get_by_role('button',name='Registros de B, Total geral',exact=True)).to_have_text('40')
    copied=next(x for x in page.request.get(base+'/api/items').json()['items'] if x['title']=='Cópia '+title)
    assert page.request.post(base+'/api/items/'+copied['id'],headers={'Origin':base},data={'title':copied['title'],'content':copied['content'],'version':copied['version'],'deleted':True}).ok
    ctx=page.context.browser.new_context();reader=ctx.new_page();credentials={'email':uuid.uuid4().hex+'@example.org','password':uuid.uuid4().hex+'-Reader12'};headers={'Origin':base}
    assert reader.request.post(base+'/api/register',headers=headers,data={**credentials,'name':'Leitor'}).ok
    assert reader.request.post(base+'/api/login',headers=headers,data=credentials).ok
    assert page.request.post(base+'/api/items/'+item['id']+'/share',headers=headers,data={'email':credentials['email'],'role':'read'}).ok
    reader.goto(base);reader.get_by_role('button',name=title,exact=False).click();expect(reader.locator('#spreadsheet')).to_have_attribute('data-ready','true')
    expect(reader.locator('#sheet-pivot-add')).to_be_disabled();expect(reader.locator('[data-pivot-edit]')).to_have_count(0);expect(reader.locator('#sheet-pivots').get_by_role('button',name='Registros de B, Total geral',exact=True)).to_have_text('40')
    assert page.request.post(base+'/api/items/'+item['id']+'/share',headers=headers,data={'email':credentials['email'],'role':'remove'}).ok
    reader.request.post(base+'/api/logout',headers=headers,data={});ctx.close()
    assert not errors,errors
    page.screenshot(path='/tmp/drap-pivot-verified.png',full_page=True)
    print('PASS: tabela dinâmica, média ponderada, filtro, cálculo atualizado, registros, XLSX, JSON e modo leitura',flush=True)
    return item

def main():
    expect.set_options(timeout=15000)
    with tempfile.TemporaryDirectory() as tmp:
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(tmp)/'test.sqlite')));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));page=browser.new_page(viewport={'width':1600,'height':1100});page.set_default_timeout(15000)
                exercise(page,f'http://127.0.0.1:{server.server_port}');browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
