"""Create, persist, query and revoke a relationship using real browser controls."""
import os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.store import Store
from server.workspace import Workspace
from server.app import handler_for

def exercise(page,base,account,target_id):
    assert page.request.post(base+'/api/login',data=account).ok
    page.goto(base)
    page.locator('[data-open]',has_text='Clientes').click()
    page.get_by_role('button',name='Vincular tabela',exact=True).click()
    page.get_by_label('Nome do relacionamento',exact=True).fill('Pedidos do cliente')
    page.get_by_label('Tabela vinculada',exact=True).select_option(target_id)
    expect(page.get_by_label('Campo da tabela vinculada',exact=True)).to_be_enabled()
    page.get_by_label('Campo da tabela vinculada',exact=True).select_option('0')
    page.get_by_role('button',name='Criar vínculo',exact=True).click()
    page.get_by_role('button',name='Salvar',exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão 2')
    page.get_by_role('button',name='Consultar Pedidos do cliente',exact=True).click()
    expect(page.locator('#modal')).to_contain_text('2 registro(s)')
    expect(page.locator('#modal')).to_contain_text('P1')
    expect(page.locator('#modal')).not_to_contain_text('P3')
    page.get_by_role('button',name='Fechar',exact=True).click()
    page.reload();page.locator('[data-open]',has_text='Clientes').click()
    expect(page.get_by_role('button',name='Consultar Pedidos do cliente',exact=True)).to_be_visible()
    print('PASS: criação, persistência, consulta por registro e reabertura dos relacionamentos')

def main():
    with tempfile.TemporaryDirectory() as temp:
        store=Store(Path(temp)/'relations.sqlite');ws=Workspace(store)
        account={'email':'relations@example.org','name':'Ana','password':'long-test-password'}
        a=store.register(**account,question='pet',answer='Rex')['id']
        other={'email':'reader@example.org','name':'Bia','password':'long-test-password'}
        b=store.register(**other,question='pet',answer='Rex')['id']
        target=ws.create(a,{'kind':'table','title':'Pedidos','content':{'columns':['Cliente','Pedido'],'rows':[['A','P1'],['A','P2'],['B','P3']]}})
        source=ws.create(a,{'kind':'table','title':'Clientes','content':{'columns':['Código'],'rows':[['A'],['B']]}})
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'))
                page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(5000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                try:exercise(page,base,account,target['id'])
                except Exception:
                    print('MODAL',page.locator('#modal').inner_text(), 'JS', errors,flush=True)
                    raise
                ws.share(a,source['id'],other['email'],'read');ws.share(a,target['id'],other['email'],'read')
                context=browser.new_context();reader=context.new_page()
                assert reader.request.post(base+'/api/login',data=other).ok
                reader.goto(base);reader.locator('[data-open]',has_text='Clientes').click()
                expect(reader.locator('#add-table-relation')).to_have_count(0)
                expect(reader.get_by_role('button',name='Consultar Pedidos do cliente',exact=True)).to_be_enabled()
                reader.get_by_role('button',name='Consultar Pedidos do cliente',exact=True).click()
                expect(reader.locator('#modal')).to_contain_text('P1');reader.get_by_role('button',name='Fechar',exact=True).click()
                ws.share(a,target['id'],other['email'],'remove')
                reader.get_by_role('button',name='Consultar Pedidos do cliente',exact=True).click()
                expect(reader.locator('#notice')).to_contain_text('sem acesso')
                assert not errors,errors;browser.close()
                print('PASS: consulta somente leitura e revogação do acesso à tabela vinculada')
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
