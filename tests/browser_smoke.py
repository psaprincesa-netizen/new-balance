"""Optional real-browser acceptance checks. Requires Playwright and Chromium."""
import os
import tempfile
import threading
import uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from server.app import handler_for
from server.store import Store
from server.database import PostgresStore


def main():
    with tempfile.TemporaryDirectory() as temp:
        store = PostgresStore(os.environ['TEST_DATABASE_URL']) if os.environ.get('TEST_DATABASE_URL') else Store(Path(temp) / 'ui.sqlite')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                page = browser.new_page(viewport={'width':1440,'height':1000})
                errors = []
                page.set_default_timeout(10000)
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' and '401' not in msg.text and '404' not in msg.text else None)
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.get_by_role('button', name='Criar minha conta').click()
                page.get_by_label('Nome', exact=True).fill('Ana Teste')
                page.get_by_label('E-mail', exact=True).fill(uuid.uuid4().hex+'@example.org')
                page.get_by_label('Senha', exact=True).fill('senha-longa-de-teste-123')
                page.get_by_role('button', name='Criar conta', exact=False).click()
                expect(page.get_by_role('heading', name='Olá, Ana. Vamos criar?')).to_be_visible()
                page.screenshot(path='/tmp/nexo-desktop.png', full_page=True)
                with page.expect_download() as download_info:
                    page.get_by_role('link',name='Baixar plataforma',exact=True).click()
                downloaded = download_info.value
                assert downloaded.suggested_filename == 'drap-office.zip'
                assert downloaded.failure() is None


                def create(kind, title):
                    print('Testing editor:', kind, flush=True)
                    page.get_by_role('button', name='Todos os arquivos', exact=False).click()
                    page.get_by_role('button', name='＋ Criar novo').click()
                    page.locator('#create-form select').select_option(kind)
                    page.get_by_label('Nome do arquivo', exact=True).last.fill(title)
                    page.get_by_role('button', name='Criar arquivo', exact=True).click()
                    expect(page.locator('#title')).to_have_value(title)

                def save():
                    page.get_by_role('button', name='Salvar', exact=True).click()
                    expect(page.locator('#save-state')).to_contain_text('Versão')

                create('document','Plano integrado')
                if page.get_by_role('button',name='Editar Markdown',exact=True).is_visible():page.get_by_role('button',name='Editar Markdown',exact=True).click()
                page.get_by_label('Conteúdo do documento').fill('# Estratégia\n\n**Planejar** o próximo trimestre.\n\n## Entrega\nConectar as ferramentas.')
                save()
                page.reload()
                page.get_by_role('button', name='Plano integrado', exact=False).click()
                expect(page.get_by_label('Conteúdo do documento')).to_contain_text('Estratégia')
                page.get_by_role('button', name='Criar apresentação ↗').click()
                expect(page.locator('#title')).to_have_value('Plano integrado — Apresentação')
                page.get_by_role('button', name='▷ Apresentar').click()
                expect(page.locator('.present h1')).to_have_text('Estratégia')
                page.keyboard.press('ArrowRight')
                expect(page.locator('.present h1')).to_have_text('Entrega')
                page.keyboard.press('Escape')

                create('sheet','Orçamento')
                expect(page.locator('#spreadsheet')).to_have_attribute('data-ready','true')
                for label,value in [('A1','Produto'),('B1','10'),('A2','Serviço'),('B2','20'),('C1','=SOMA(B1:B2)')]:
                    page.locator('#sheet-address').fill(label)
                    page.locator('#sheet-value').fill(value)
                    page.locator('#sheet-apply').click()
                save()
                page.get_by_role('button', name='Criar relatório ↗').click()
                expect(page.get_by_label('Conteúdo do documento')).to_contain_text('Produto | 10 | 30')

                create('board','Lançamento')
                page.get_by_label('Nome da tarefa').fill('Revisar documento')
                page.get_by_label('Prazo',exact=True).fill('2026-11-10')
                page.get_by_role('button',name='＋ Adicionar tarefa').click()
                page.get_by_label('Estado de Revisar documento').select_option('Concluído')
                save()
                expect(page.locator('.column').filter(has=page.get_by_role('heading',name='Concluído',exact=False))).to_contain_text('Revisar documento')

                create('calendar','Agenda da equipe')
                page.get_by_label('Título do evento').fill('Planejamento')
                page.get_by_label('Data e hora de início').fill('2026-11-10T10:00')
                page.get_by_label('Data e hora de fim').fill('2026-11-10T11:00')
                page.get_by_role('button',name='＋ Adicionar',exact=True).click()
                save()
                expect(page.get_by_role('heading',name='Planejamento',exact=True)).to_be_visible()

                create('form','Pesquisa')
                page.get_by_label('Como podemos melhorar?').fill('Integração dos dados')
                page.get_by_role('button',name='Registrar resposta').click()
                save()
                page.get_by_role('button',name='Respostas → Tabela').click()
                expect(page.get_by_label('Registro 1, Como podemos melhorar?')).to_have_value('Integração dos dados')
                page.get_by_role('button',name='Abrir como planilha ↗').click()
                expect(page.locator('#spreadsheet')).to_have_attribute('data-ready','true')
                page.locator('#sheet-address').fill('B2');page.locator('#sheet-select').click()
                expect(page.locator('#sheet-value')).to_have_value('Integração dos dados')

                create('diagram','Fluxo')
                page.get_by_label('Etapa 2').fill('Aprovação')
                page.get_by_role('button',name='＋ Etapa').click()
                save()
                expect(page.locator('.node').nth(1)).to_have_text('Aprovação')

                create('note','Ideias')
                if page.get_by_role('button',name='Editar Markdown',exact=True).is_visible():page.get_by_role('button',name='Editar Markdown',exact=True).click()
                page.get_by_label('Conteúdo do documento').fill('Uma anotação integrada.')
                save()
                page.get_by_role('button',name='Mover para lixeira').click()
                page.get_by_role('button',name='Confirmar',exact=True).click()
                expect(page.get_by_role('button',name='Restaurar',exact=True)).to_be_visible()
                page.get_by_role('button',name='Restaurar',exact=True).click()
                page.get_by_role('button',name='Confirmar',exact=True).click()
                expect(page.get_by_role('button',name='Mover para lixeira')).to_be_visible()
                page.get_by_role('button',name='Histórico',exact=True).click()
                page.locator('[data-version="1"]').click()
                save()
                expect(page.get_by_label('Conteúdo do documento')).to_have_value('')

                create('portal','Central')
                page.get_by_label('Boas-vindas').fill('# Nosso espaço\nArquivos conectados.')
                page.get_by_label('Arquivo para vincular').select_option(label='Plano integrado')
                page.get_by_role('button',name='Vincular arquivo').click()
                save()
                expect(page.get_by_role('button',name='Plano integrado ↗')).to_be_visible()
                page.get_by_label('Buscar arquivos').fill('Plano integrado')
                expect(page.locator('#file-list')).to_contain_text('Plano integrado')
                page.locator('[data-open]').first.click()
                expect(page.locator('#editor-body')).to_be_visible()
                page.get_by_role('button',name='Indicadores',exact=False).click()
                expect(page.locator('.metrics')).to_contain_text('1/1')
                page.get_by_role('button',name='Visão geral',exact=False).click()
                page.set_viewport_size({'width':390,'height':844})
                page.screenshot(path='/tmp/nexo-mobile.png',full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile overflow'
                assert not errors, errors
                browser.close()
                print('Browser acceptance passed: all 10 editors, persistence, conversions, formulas, presentation keyboard, tasks, events, trash, restore, analytics, mobile. No JS/CSP errors.')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    main()
