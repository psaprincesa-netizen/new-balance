"""Real-browser checks for stage 2: document layout tools and new spreadsheet charts."""
import io
import os
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from docx import Document
from playwright.sync_api import sync_playwright, expect
from server.app import handler_for
from server.store import Store
from server.database import PostgresStore
from tests.browser_projects import signup
from tests.browser_sheet_links import create


def documents(page):
    create(page, 'document', 'Relatório anual')
    editor = page.locator('.visual-document')
    expect(editor).to_be_visible()
    page.get_by_role('button', name='Editar Markdown').click()
    page.locator('#text').fill('# Introdução\n\nTexto da introdução.\n\n## Resultados\n\nTexto dos resultados.')
    page.get_by_role('button', name='Editar visualmente').click()
    expect(editor.locator('h2', has_text='Resultados')).to_be_visible()

    # Page break after the introduction text (visual editor command).
    editor.locator('p', has_text='Texto da introdução.').click()
    page.keyboard.press('End')
    page.get_by_role('button', name='Quebra de página').click()
    expect(editor.locator('hr.page-break')).to_have_count(1)
    expect(editor.locator('hr.page-break + h2', has_text='Resultados')).to_have_count(1)

    # Table of contents after the first heading.
    editor.locator('h1', has_text='Introdução').click()
    page.keyboard.press('End')
    page.get_by_role('button', name='Sumário').click()
    expect(editor.locator('h2', has_text='Sumário')).to_be_visible()
    expect(editor.locator('li', has_text='Resultados').last).to_be_visible()

    page.get_by_role('button', name='Cabeçalho e rodapé').click()
    page.get_by_label('Cabeçalho').fill('Empresa Exemplo')
    page.get_by_label('Rodapé').fill('Uso interno')
    page.get_by_label('Numerar páginas (Página X de Y)').check()
    page.get_by_role('button', name='Aplicar').click()
    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão')

    page.reload()
    page.get_by_role('button', name='Todos os arquivos').click()
    page.get_by_text('Relatório anual', exact=True).first.click()
    expect(page.locator('.visual-document hr.page-break')).to_have_count(1)
    page.get_by_role('button', name='Editar Markdown').click()
    text = page.locator('#text').input_value()
    assert '---' in text and '## Sumário' in text and '- Resultados' in text.replace('  ', ''), text
    page.get_by_role('button', name='Editar visualmente').click()

    # The printed page breaks before "Resultados".
    page.emulate_media(media='print')
    assert page.evaluate("getComputedStyle(document.querySelector('.visual-document hr.page-break')).breakAfter") == 'page'
    page.emulate_media(media='screen')

    with page.expect_download() as download:
        page.get_by_role('button', name='Baixar DOCX').click()
    doc = Document(io.BytesIO(Path(download.value.path()).read_bytes()))
    assert doc.sections[0].header.paragraphs[0].text == 'Empresa Exemplo'
    assert 'NUMPAGES' in doc.sections[0].footer.paragraphs[0]._p.xml
    assert 'w:type="page"' in doc.element.body.xml


def charts(page):
    page.get_by_role('button', name='Visão geral').click()
    create(page, 'sheet', 'Vendas por mês')
    expect(page.locator('#spreadsheet')).to_have_attribute('data-ready', 'true', timeout=30000)
    page.get_by_role('button', name='Colar tabela').click()
    page.get_by_label('Célula inicial').fill('A1')
    page.get_by_label('Dados copiados do Excel ou CSV').fill('Mês\tReceita\tCusto\nJan\t10\t4\nFev\t12\t5\nMar\t8\t3')
    page.get_by_role('button', name='Colar dados').click()
    for chart_type, label in [('stacked', 'Colunas empilhadas'), ('area', 'Área'), ('hbar', 'Barras horizontais')]:
        page.get_by_role('button', name='Criar gráfico').click()
        page.get_by_label('Título do gráfico').fill(label)
        page.get_by_label('Tipo de gráfico').select_option(chart_type)
        page.get_by_label('Intervalo de dados').fill('A1:C4')
        page.get_by_role('button', name='Adicionar gráfico').click()
        expect(page.locator('.sheet-chart', has_text=label).locator('svg')).to_contain_text('Custo')
    # Pie keeps a single series.
    page.get_by_role('button', name='Criar gráfico').click()
    page.get_by_label('Tipo de gráfico').select_option('pie')
    page.get_by_label('Intervalo de dados').fill('A1:C4')
    page.get_by_role('button', name='Adicionar gráfico').click()
    expect(page.locator('#chart-error')).to_contain_text('duas colunas')
    page.keyboard.press('Escape')
    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão')
    with page.expect_download() as download:
        page.get_by_role('button', name='Baixar XLSX').click()
    from openpyxl import load_workbook
    kinds = [type(c).__name__ for c in load_workbook(io.BytesIO(Path(download.value.path()).read_bytes())).worksheets[0]._charts]
    assert kinds == ['BarChart', 'AreaChart', 'BarChart'], kinds


def exercise(page, base):
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    signup(page, base)
    documents(page)
    print('PASS: sumário, quebra de página, cabeçalho/rodapé com numeração, impressão e DOCX', flush=True)
    charts(page)
    print('PASS: gráficos empilhados, área, barras horizontais com várias séries e XLSX', flush=True)
    assert not errors, errors


def main():
    with tempfile.TemporaryDirectory() as temp:
        store = PostgresStore(os.environ['TEST_DATABASE_URL']) if os.environ.get('TEST_DATABASE_URL') else Store(Path(temp) / 'stage2.sqlite')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                page = browser.new_page(viewport={'width': 1600, 'height': 1100}, accept_downloads=True)
                page.set_default_timeout(20000)
                exercise(page, f'http://127.0.0.1:{server.server_port}')
                browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
