"""Real-browser check of quiz forms, multiple selection and scale questions. Requires Playwright and Chromium."""
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


def exercise(browser, page, base):
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    signup(page, base)
    page.get_by_role('button', name='＋ Criar novo').click()
    page.locator('#create-form select').select_option('form')
    page.get_by_label('Nome do arquivo', exact=True).last.fill('Quiz de geografia')
    page.get_by_role('button', name='Criar arquivo', exact=True).click()
    expect(page.locator('#title')).to_have_value('Quiz de geografia')

    # Question 1: single choice; question 2: multiple selection; question 3: scale.
    page.get_by_label('Pergunta 1', exact=True).fill('Capital do Brasil')
    page.get_by_label('Tipo da pergunta 1').select_option('choice')
    page.get_by_label('Opções da pergunta 1').fill('Brasília\nRio de Janeiro')
    page.get_by_label('Opções da pergunta 1').blur()
    page.get_by_role('button', name='＋ Pergunta de texto').click()
    page.get_by_label('Pergunta 2', exact=True).fill('Estados do Sul')
    page.get_by_label('Tipo da pergunta 2').select_option('multiple')
    page.get_by_label('Opções da pergunta 2').fill('Paraná\nBahia\nRio Grande do Sul')
    page.get_by_label('Opções da pergunta 2').blur()
    page.get_by_role('button', name='＋ Pergunta de texto').click()
    page.get_by_label('Pergunta 3', exact=True).fill('Dificuldade')
    page.get_by_label('Tipo da pergunta 3').select_option('scale')
    page.get_by_label('Máximo da escala da pergunta 3').select_option('7')

    page.get_by_label('Modo quiz (nota automática)').check()
    page.get_by_label('Resposta correta da pergunta 1').select_option('Brasília')
    page.get_by_label('Pontos da pergunta 1').fill('3')
    page.get_by_label('Pontos da pergunta 1').blur()
    page.locator('[data-correct-multi="1"][value="Paraná"]').check()
    page.locator('[data-correct-multi="1"][value="Rio Grande do Sul"]').check()

    # Answer inside the editor: 3 + 1 points.
    form = page.locator('#respond-form')
    form.get_by_label('Capital do Brasil *').select_option('Brasília')
    form.get_by_label('Paraná').check()
    form.get_by_label('Rio Grande do Sul').check()
    form.get_by_label('5', exact=True).check()
    form.get_by_role('button', name='Registrar resposta').click()
    expect(page.get_by_text('Nota: 4 de 4').first).to_be_visible()
    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão')

    # Public link: the answer key is not sent and the score comes from the server.
    page.get_by_role('button', name='Link de coleta').click()
    page.get_by_role('button', name='Ativar link público').click()
    url = page.locator('#public-link').input_value()
    page.get_by_role('button', name='Fechar').click()
    public = browser.new_context().new_page()
    schema_bodies = []
    public.on('response', lambda r: schema_bodies.append(r.text()) if '/api/forms/' in r.url and r.request.method == 'GET' else None)
    public.goto(url)
    expect(public.get_by_role('heading', name='Quiz de geografia')).to_be_visible()
    assert schema_bodies and 'correct' not in schema_bodies[0] and 'Brasília' in schema_bodies[0]
    public.get_by_label('Capital do Brasil *').select_option('Rio de Janeiro')
    public.get_by_label('Paraná').check()
    public.get_by_label('Rio Grande do Sul').check()
    public.get_by_label('2', exact=True).check()
    public.get_by_role('button', name='Enviar resposta').click()
    expect(public.locator('#quiz-score')).to_have_text('Sua nota: 1 de 4')

    page.reload()
    page.locator('[data-open]').filter(has_text='Quiz de geografia').first.click()
    expect(page.get_by_text('Nota: 1 de 4')).to_be_visible()
    assert not errors, errors
    print('PASS: múltipla seleção, escala, quiz com nota no editor e no link público sem expor o gabarito', flush=True)


def main():
    with tempfile.TemporaryDirectory() as temp:
        store = PostgresStore(os.environ['TEST_DATABASE_URL']) if os.environ.get('TEST_DATABASE_URL') else Store(Path(temp) / 'quiz.sqlite')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.set_default_timeout(15000)
                exercise(browser, page, f'http://127.0.0.1:{server.server_port}')
                browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
