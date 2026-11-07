"""Delete one listed file, cancel, restore, and hide mutation controls for readers."""
import os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.app import handler_for
from server.store import Store
from server.workspace import Workspace

def exercise(page,base,account):
    assert page.request.post(base+'/api/login',data=account).ok
    page.goto(base)
    page.get_by_role('button',name='Todos os arquivos',exact=False).click()
    expect(page.locator('[data-open]')).to_have_count(3)
    page.get_by_role('button',name='Excluir Primeiro',exact=True).click()
    page.get_by_role('button',name='Cancelar',exact=True).click()
    expect(page.locator('[data-open]')).to_have_count(3)
    expect(page.get_by_role('button',name='Excluir Somente leitura',exact=True)).to_have_count(0)
    page.get_by_role('button',name='Excluir Primeiro',exact=True).click()
    page.get_by_role('button',name='Confirmar',exact=True).click()
    expect(page.locator('[data-open]')).to_have_count(2)
    expect(page.locator('[data-open]',has_text='Segundo')).to_be_visible()
    page.get_by_role('button',name='Lixeira',exact=False).click()
    expect(page.locator('[data-open]')).to_have_count(1)
    page.get_by_role('button',name='Restaurar Primeiro',exact=True).click()
    page.get_by_role('button',name='Confirmar',exact=True).click()
    expect(page.locator('[data-open]')).to_have_count(0)
    page.get_by_role('button',name='Todos os arquivos',exact=False).click()
    expect(page.locator('[data-open]')).to_have_count(3)
    page.set_viewport_size({'width':390,'height':844})
    expect(page.get_by_role('button',name='Excluir Primeiro',exact=True)).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    print('PASS: exclusão individual, cancelar, demais arquivos preservados, restaurar, leitura e celular')

def main():
    with tempfile.TemporaryDirectory() as temp:
        store=Store(Path(temp)/'delete.sqlite');ws=Workspace(store)
        account={'email':'delete@example.org','name':'Ana','password':'long-test-password'}
        user=store.register(**account,question='pet',answer='Rex')['id'];other=store.register('other@example.org','Bia','another-test-password')['id']
        for title in ['Primeiro','Segundo']:ws.create(user,{'kind':'document','title':title,'content':{'text':title}})
        shared=ws.create(other,{'kind':'document','title':'Somente leitura','content':{'text':'Privado'}})
        ws.share(other,shared['id'],account['email'],'read')
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'))
                page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                exercise(page,f'http://127.0.0.1:{server.server_port}',account)
                assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
