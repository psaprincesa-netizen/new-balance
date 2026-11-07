import os
"""Diagram shapes, labels, templates, SVG and persistence through real UI."""
import tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.app import handler_for
from server.store import Store
from tests.browser_projects import signup

def exercise(page,base):
    signup(page,base)
    page.get_by_role('button',name='＋ Criar novo').click()
    page.locator('#create-form select').select_option('diagram')
    page.get_by_label('Nome do arquivo',exact=True).last.fill('Diagrama sintético')
    page.get_by_role('button',name='Criar arquivo',exact=True).click()
    page.get_by_label('Modelo de diagrama').select_option('flow')
    page.get_by_role('button',name='Criar novo a partir do modelo').click()
    expect(page.get_by_label('Nome do arquivo',exact=True)).to_have_value('Fluxograma de aprovação')
    expect(page.get_by_label('Forma da etapa 3',exact=True)).to_have_value('decision')
    expect(page.locator('[data-edge-label="2"]')).to_have_text('Sim')
    page.get_by_label('Forma da etapa 1',exact=True).select_option('document')
    page.get_by_role('button',name='Salvar',exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão 2')
    with page.expect_download() as event:page.get_by_role('button',name='Baixar SVG',exact=True).click()
    svg=Path(event.value.path()).read_text();assert '<polygon' in svg and '>Sim</text>' in svg
    page.reload()
    page.locator('[data-open]').filter(has_text='Fluxograma de aprovação').first.click()
    expect(page.get_by_label('Forma da etapa 1',exact=True)).to_have_value('document')
    expect(page.locator('[data-edge-label="2"]')).to_have_text('Sim')
    print('PASS: modelos, formas, rótulos, SVG, salvamento e reabertura de diagramas')

def main():
    with tempfile.TemporaryDirectory() as temp:
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(temp)/'diagram.sqlite')))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'))
                page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                exercise(page,f'http://127.0.0.1:{server.server_port}')
                assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
