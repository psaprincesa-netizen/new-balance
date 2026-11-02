"""Real-browser check of the spreadsheet "＋ Inserir" button: links from cells to DRAP files and sites."""
import os
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from server.app import handler_for
from server.store import Store
from server.database import PostgresStore
from tests.browser_projects import signup


def create(page, kind, title):
    page.get_by_role('button', name='＋ Criar novo').click()
    page.locator('#create-form select').select_option(kind)
    page.get_by_label('Nome do arquivo', exact=True).last.fill(title)
    page.get_by_role('button', name='Criar arquivo', exact=True).click()
    expect(page.locator('#title')).to_have_value(title)


def exercise(page, base):
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    signup(page, base)
    create(page, 'document', 'Contrato de serviço')
    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão')
    page.get_by_role('button', name='Visão geral').click()
    create(page, 'sheet', 'Controle de contratos')
    expect(page.locator('#spreadsheet')).to_have_attribute('data-ready', 'true', timeout=30000)

    # Link a DRAP file to B2.
    page.locator('#aux-insert').click();page.locator('#insert-cell-link').click()
    page.get_by_label('Arquivo a vincular').select_option(label='Contrato de serviço — Documento')
    page.get_by_label('Célula de destino').fill('B2')
    page.get_by_role('button', name='Inserir', exact=True).click()
    expect(page.locator('#sheet-link-bar')).to_contain_text('Contrato de serviço')
    expect(page.locator('#sheet-links')).to_contain_text('Contrato de serviço')

    # Link an external site to C2 with custom text; http is refused.
    page.get_by_label('Intervalo da planilha').fill('C2')
    page.get_by_role('button', name='Vincular célula',exact=True).click()
    page.get_by_label('Link externo (site)').check()
    page.get_by_label('Endereço (https)').fill('http://exemplo.com')
    page.get_by_label('Texto exibido na célula').fill('Portal do cliente')
    page.get_by_role('button', name='Inserir', exact=True).click()
    expect(page.locator('#insert-link-error')).to_contain_text('https')
    page.get_by_label('Endereço (https)').fill('https://exemplo.com/cliente')
    page.get_by_role('button', name='Inserir', exact=True).click()
    expect(page.locator('#sheet-links li')).to_have_count(2)
    page.get_by_label('Intervalo da planilha').fill('C2')
    page.get_by_role('button', name='Selecionar').click()
    expect(page.get_by_label('Valor ou fórmula')).to_have_value('Portal do cliente')

    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão')

    # After reopening, selecting B2 shows the link and opens the document.
    page.reload()
    page.get_by_role('button', name='Todos os arquivos').click()
    page.get_by_text('Controle de contratos', exact=True).first.click()
    expect(page.locator('#spreadsheet')).to_have_attribute('data-ready', 'true', timeout=30000)
    expect(page.locator('#sheet-links li')).to_have_count(2)
    page.get_by_label('Intervalo da planilha').fill('B2')
    page.get_by_role('button', name='Selecionar').click()
    expect(page.get_by_label('Valor ou fórmula')).to_have_value('Contrato de serviço')
    expect(page.locator('#sheet-link-bar')).to_be_visible()
    # Clicking another cell hides the bar; clicking B2 in the grid shows it again.
    # Find B2 on the canvas from the row/column headers rendered by the editor.
    box = page.locator('#spreadsheet canvas').first.bounding_box()
    def cell_at(x, y):
        page.mouse.click(box['x'] + x, box['y'] + y)
        page.wait_for_timeout(200)  # the address field updates after the selection event
        return page.get_by_label('Intervalo da planilha').input_value()
    # Cells are about 105 x 25 px; scan a column of points and click the middle of B2.
    hits = [y for y in range(-10, 80, 3) if cell_at(40, y) == 'B2']
    target = (40, hits[len(hits) // 2]) if hits else None
    other = (150, 100)
    assert target and cell_at(*other) not in ('B2', ''), 'B2 not found on the canvas'
    page.mouse.click(box['x'] + other[0], box['y'] + other[1])
    expect(page.locator('#sheet-link-bar')).to_be_hidden()
    page.mouse.click(box['x'] + target[0], box['y'] + target[1])
    expect(page.get_by_label('Intervalo da planilha')).to_have_value('B2')
    expect(page.locator('#sheet-link-bar')).to_be_visible()
    page.get_by_role('button', name='Abrir arquivo ↗').click()
    expect(page.locator('#title')).to_have_value('Contrato de serviço')
    assert not errors, errors
    print('PASS: ＋ Inserir vincula arquivos do DRAP e links https a células, persiste e abre o arquivo', flush=True)


def main():
    with tempfile.TemporaryDirectory() as temp:
        store = PostgresStore(os.environ['TEST_DATABASE_URL']) if os.environ.get('TEST_DATABASE_URL') else Store(Path(temp) / 'links.sqlite')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                page = browser.new_page(viewport={'width': 1600, 'height': 1100})
                page.set_default_timeout(20000)
                exercise(page, f'http://127.0.0.1:{server.server_port}')
                browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
