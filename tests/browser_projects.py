"""Real-browser check of project dependencies, timeline and critical path. Requires Playwright and Chromium."""
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


def signup(page, base):
    page.goto(base)
    page.get_by_role('button', name='Criar minha conta').click()
    page.get_by_label('Nome', exact=True).fill('Paula Teste')
    page.get_by_label('E-mail', exact=True).fill(uuid.uuid4().hex + '@example.org')
    page.get_by_label('Senha', exact=True).fill('senha-longa-de-teste-123')
    page.get_by_label('Pergunta secreta', exact=True).select_option(index=1)
    page.get_by_label('Resposta secreta', exact=True).fill('resposta de teste')
    page.get_by_role('button', name='Criar conta', exact=False).click()
    expect(page.get_by_role('heading', name='Olá, Paula. Vamos criar?')).to_be_visible()


def exercise(page, base):
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    signup(page, base)
    page.get_by_role('button', name='＋ Criar novo').click()
    page.locator('#create-form select').select_option('board')
    page.get_by_label('Nome do arquivo', exact=True).last.fill('Lançamento')
    page.get_by_role('button', name='Criar arquivo', exact=True).click()
    expect(page.locator('#title')).to_have_value('Lançamento')

    for title, start, due in [('Pesquisa', '2026-03-02', '2026-03-04'), ('Design', '2026-03-05', '2026-03-11'),
                              ('Textos', '2026-03-05', '2026-03-06'), ('Publicação', '2026-03-12', '2026-03-13')]:
        page.get_by_label('Nome da tarefa').fill(title)
        page.get_by_label('Início', exact=True).fill(start)
        page.get_by_label('Prazo', exact=True).fill(due)
        page.get_by_role('button', name='＋ Adicionar tarefa').click()
        expect(page.get_by_role('heading', name=title)).to_be_visible()

    def depend(title, *on):
        page.locator('article.card', has=page.get_by_role('heading', name=title, exact=True)).get_by_role('button', name='Detalhes').click()
        for other in on:
            page.locator('.task-deps').get_by_label(other, exact=True).check()
        page.get_by_role('button', name='Aplicar detalhes').click()
        expect(page.locator('#task-details')).to_have_count(0)

    page.locator('article.card', has=page.get_by_role('heading', name='Design', exact=True)).get_by_role('button', name='Detalhes').click()
    for label, value in [('Responsável','Ana'), ('Horas planejadas','10'), ('Horas realizadas','12'), ('Custo por hora','50'), ('Custos adicionais','100')]:
        page.get_by_label(label, exact=True).fill(value)
    page.get_by_role('button', name='Aplicar detalhes').click()
    page.locator('#project-budget summary').click()
    expect(page.locator('#project-budget')).to_contain_text('600,00')
    expect(page.locator('#project-budget')).to_contain_text('700,00')
    expect(page.locator('#project-budget tbody')).to_contain_text('Ana')

    page.locator('#project-capacity summary').first.click()
    page.get_by_label('Responsável pela capacidade', exact=True).fill('Ana')
    page.get_by_label('Capacidade diária (horas)').fill('1')
    page.get_by_role('button', name='Definir capacidade', exact=True).click()
    page.locator('#project-capacity summary').first.click()
    expect(page.locator('#project-capacity tbody')).to_contain_text('Ana')
    expect(page.locator('#project-capacity tbody')).to_contain_text('7')
    page.locator('#project-baseline summary').click()
    page.get_by_role('button', name='Registrar linha de base', exact=True).click()
    page.locator('article.card', has=page.get_by_role('heading', name='Design', exact=True)).get_by_role('button', name='Detalhes').click()
    page.get_by_label('Horas planejadas', exact=True).fill('20')
    page.get_by_role('button', name='Aplicar detalhes').click()
    page.locator('#project-baseline summary').click()
    expect(page.locator('#baseline-cost-delta')).to_contain_text('500,00')

    depend('Design', 'Pesquisa')
    depend('Textos', 'Pesquisa')
    depend('Publicação', 'Design', 'Textos')
    expect(page.get_by_text('Depende de: Design, Textos')).to_be_visible()

    # A dependency back to a successor would create a cycle and is refused.
    page.locator('article.card', has=page.get_by_role('heading', name='Pesquisa', exact=True)).get_by_role('button', name='Detalhes').click()
    page.locator('.task-deps').get_by_label('Publicação', exact=True).check()
    page.get_by_role('button', name='Aplicar detalhes').click()
    expect(page.locator('#task-error')).to_contain_text('ciclo')
    page.keyboard.press('Escape')

    page.get_by_role('button', name='Cronograma', exact=True).click()
    expect(page.locator('#critical-path')).to_have_text('Pesquisa → Design → Publicação')
    expect(page.get_by_text('2026-03-02 a 2026-03-13 (12 dias)', exact=False)).to_be_visible()
    expect(page.locator('.gantt-row.critical')).to_have_count(3)
    expect(page.locator('[data-gantt]', has_text='Textos')).to_contain_text('folga 5 d')

    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão')
    page.reload()
    page.locator('[data-open]').filter(has_text='Lançamento').first.click()
    page.get_by_role('button', name='Cronograma', exact=True).click()
    expect(page.locator('#critical-path')).to_have_text('Pesquisa → Design → Publicação')
    expect(page.locator('#project-budget summary')).to_contain_text('1.100,00')
    expect(page.locator('#project-budget summary')).to_contain_text('700,00')
    page.locator('#project-baseline summary').click()
    expect(page.locator('#baseline-cost-delta')).to_contain_text('500,00')
    assert not errors, errors
    print('PASS: dependências, ciclo bloqueado, cronograma, caminho crítico, folga e persistência', flush=True)


def main():
    with tempfile.TemporaryDirectory() as temp:
        store = PostgresStore(os.environ['TEST_DATABASE_URL']) if os.environ.get('TEST_DATABASE_URL') else Store(Path(temp) / 'projects.sqlite')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.set_default_timeout(15000)
                exercise(page, f'http://127.0.0.1:{server.server_port}')
                browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
