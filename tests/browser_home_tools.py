import os
"""Home tools open locally; only an explicit first save requires a name."""
import tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.app import handler_for
from server.store import Store
from tests.browser_projects import signup

def exercise(page,base):
    errors=[];writes=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.on('request',lambda r:writes.append(r.url) if r.method=='POST' and '/api/items' in r.url else None)
    signup(page,base)
    kinds=['document','sheet','slides','note','board','calendar','form','table','diagram','portal']
    for kind in kinds:
        page.locator(f'[data-create="{kind}"]').click()
        expect(page.locator('#editor-body')).to_be_visible()
        expect(page.locator('#create-form')).to_have_count(0)
        expect(page.get_by_label('Nome do arquivo',exact=True)).to_have_value('')
        expect(page.locator('#save-state')).to_contain_text('Ainda não salvo')
        page.get_by_role('button',name='Visão geral',exact=False).click()
        if page.locator('#yes').is_visible():page.locator('#yes').click()
    assert writes==[],writes
    page.locator('[data-create="document"]').click()
    expect(page.locator('#preview')).to_have_attribute('data-ready','true')
    page.locator('#preview [contenteditable=true]').fill('Texto antes de escolher um nome.')
    page.get_by_role('button',name='Salvar',exact=True).click()
    expect(page.get_by_label('Nome do projeto')).to_be_visible()
    page.get_by_role('button',name='Continuar editando',exact=True).click()
    expect(page.locator('#preview')).to_contain_text('Texto antes de escolher um nome.')
    assert not writes,writes
    page.wait_for_timeout(400) # Draft persistence is debounced by 300 ms.
    assert page.evaluate("Object.keys(localStorage).some(k=>k.includes('local-document'))")
    page.on('dialog',lambda dialog:dialog.accept())
    page.reload()
    page.locator('[data-create=\"document\"]').click()
    expect(page.locator('#preview')).to_contain_text('Texto antes de escolher um nome.')
    with page.expect_download() as event:page.get_by_role('button',name='Baixar DOCX',exact=True).click()
    assert Path(event.value.path()).stat().st_size>100
    assert not writes,writes
    page.get_by_role('button',name='Salvar',exact=True).click()
    page.get_by_label('Nome do projeto').fill('Projeto com nome posterior')
    page.get_by_role('button',name='Salvar projeto',exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão 1')
    assert len(writes)==1,writes
    expect(page.get_by_label('Nome do arquivo',exact=True)).to_have_value('Projeto com nome posterior')
    expect(page.locator('#preview')).to_contain_text('Texto antes de escolher um nome.')
    page.get_by_role('button',name='Salvar',exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão 2')
    assert len(writes)==2,writes
    page.reload()
    page.locator('[data-open]').filter(has_text='Projeto com nome posterior').first.click()
    expect(page.locator('#preview')).to_contain_text('Texto antes de escolher um nome.')
    assert not errors,errors
    print('PASS: dez atalhos diretos, nenhuma criação antecipada, cancelar, exportar sem salvar, primeiro salvamento e reabertura')

def main():
    with tempfile.TemporaryDirectory() as temp:
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(temp)/'home.sqlite')))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'))
                page=browser.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(15000)
                exercise(page,f'http://127.0.0.1:{server.server_port}');browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
