"""A large library should not download every document to display its titles."""
import json,os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.app import handler_for
from server.store import Store
from server.workspace import Workspace

def main():
    expect.set_options(timeout=30000)
    with tempfile.TemporaryDirectory() as tmp:
        store=Store(Path(tmp)/'db.sqlite');ws=Workspace(store);account={'email':'library@example.org','name':'Ana','password':'senha-longa-para-teste'};user=store.register(**account)['id']
        board=ws.create(user,{'kind':'board','title':'Projeto rápido','content':{'tasks':[]}})
        for i in range(25):ws.create(user,{'kind':'document','title':f'Arquivo {i:02}','content':{'text':('palavraexclusiva' if i==0 else 'conteúdo')+' x'*50000}})
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));context=browser.new_context(accept_downloads=True);page=context.new_page();requests=[];errors=[]
                page.on('request',lambda r:requests.append(r.url.removeprefix(base)));page.on('pageerror',lambda e:errors.append(str(e)))
                assert page.request.post(base+'/api/login',data=account).ok
                page.goto(base);expect(page.get_by_role('heading',name='Olá, Ana. Vamos criar?')).to_be_visible()
                assert requests.count('/api/bootstrap')==1;assert not any(r.startswith('/api/items') for r in requests);assert '/formula-engine.js' not in requests;assert '/spreadsheet.js' not in requests
                resources=page.evaluate("performance.getEntriesByType('resource').filter(r=>r.name.includes('/api/')).map(r=>r.decodedBodySize)");assert sum(resources)<15000,resources
                page.get_by_role('button',name='Todos os arquivos',exact=False).click();expect(page.locator('[data-open]')).to_have_count(26)
                before=len(requests);page.get_by_role('button',name='Projeto rápido',exact=False).click();expect(page.get_by_label('Nome da tarefa',exact=True)).to_be_visible();assert len([r for r in requests[before:] if r.startswith('/api/items/')])==1
                page.get_by_label('Nome da tarefa',exact=True).fill('Conferir velocidade');page.get_by_role('button',name='＋ Adicionar tarefa').click()
                before=len(requests);page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão 2');assert not any(r.startswith('/api/library') for r in requests[before:])
                held=[];page.route('**/api/library?offset=*',lambda route:held.append(route))
                page.get_by_role('button',name='Todos os arquivos',exact=False).click();expect(page.get_by_role('heading',name='Todos os arquivos',exact=True)).to_be_visible();expect(page.locator('#editor-body')).to_have_count(0)
                expect(page.locator('#file-list')).to_have_attribute('aria-busy','true');page.get_by_label('Buscar arquivos').fill('Arquivo')
                assert held;held.pop().continue_();expect(page.locator('#file-list')).not_to_have_attribute('aria-busy','true');expect(page.get_by_label('Buscar arquivos')).to_be_focused();page.unroute('**/api/library?offset=*')
                page.get_by_label('Buscar arquivos').fill('palavraexclusiva');expect(page.locator('[data-open]')).to_have_count(1);expect(page.locator('[data-open]')).to_contain_text('Arquivo 00')
                page.get_by_label('Buscar arquivos').fill('');expect(page.locator('[data-open]')).to_have_count(26)
                with page.expect_download() as download:page.get_by_role('button',name='Exportar meu espaço',exact=True).click()
                backup=json.loads(Path(download.value.path()).read_text());assert len(backup['items'])==26;assert all('content' in item for item in backup['items']);assert any('palavraexclusiva' in item['content'].get('text','') for item in backup['items'])
                page.get_by_role('button',name='Indicadores',exact=False).click();expect(page.locator('.metrics')).to_contain_text('0/1')
                assert not errors,errors;browser.close()
                print('Library passed: 26 files, one lightweight bootstrap, lazy editors, one open request, no full reload after save, full-text search, complete backup and real analytics.')
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
