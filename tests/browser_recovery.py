"""Real-browser check of password recovery by secret question. Requires Playwright and Chromium."""
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

PASSWORD = 'senha-original-123'
NEW_PASSWORD = 'senha-renovada-456'


def login(page, email, password):
    page.get_by_label('E-mail', exact=True).fill(email)
    page.get_by_label('Senha', exact=True).fill(password)
    page.get_by_role('button', name='Entrar no DRAP office', exact=False).click()


def exercise(page, base, store):
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    email = uuid.uuid4().hex + '@example.org'

    # Sign-up requires choosing a question and an answer.
    page.goto(base)
    page.get_by_role('button', name='Criar minha conta').click()
    page.get_by_label('Nome', exact=True).fill('Rita Teste')
    page.get_by_label('E-mail', exact=True).fill(email)
    page.get_by_label('Senha', exact=True).fill(PASSWORD)
    expect(page.get_by_label('Pergunta secreta', exact=True).locator('option')).to_have_count(8)
    page.get_by_label('Pergunta secreta', exact=True).select_option('pet')
    page.get_by_label('Resposta secreta', exact=True).fill('Totó Júnior')
    page.get_by_role('button', name='Criar conta', exact=False).click()
    expect(page.get_by_role('heading', name='Olá, Rita. Vamos criar?')).to_be_visible()
    expect(page.locator('#recovery-setup')).to_have_count(0)
    page.locator('#logout').click()

    # Forgot password: wrong answer is refused, the right one sets a new password.
    page.get_by_role('button', name='Esqueci minha senha').click()
    page.get_by_label('E-mail', exact=True).fill(email)
    page.get_by_role('button', name='Continuar', exact=False).click()
    expect(page.locator('#recovery-question')).to_have_text('Qual era o nome do seu primeiro animal de estimação?')
    page.get_by_label('Resposta secreta', exact=True).fill('Rex')
    page.get_by_label('Nova senha', exact=True).fill(NEW_PASSWORD)
    page.get_by_label('Confirmar nova senha', exact=True).fill(NEW_PASSWORD)
    page.get_by_role('button', name='Criar nova senha', exact=False).click()
    expect(page.locator('#recovery-error')).to_contain_text('Não foi possível recuperar')
    page.get_by_label('Resposta secreta', exact=True).fill('  toto JUNIOR ')
    page.get_by_role('button', name='Criar nova senha', exact=False).click()
    expect(page.get_by_text('Senha alterada. Entre com a nova senha.')).to_be_visible()
    expect(page.get_by_label('E-mail', exact=True)).to_have_value(email)
    login(page, email, PASSWORD)
    expect(page.locator('#auth-error')).to_contain_text('incorretos')
    login(page, email, NEW_PASSWORD)
    expect(page.get_by_role('heading', name='Olá, Rita. Vamos criar?')).to_be_visible()

    # Change the question from the sidebar; the current password is required.
    page.get_by_role('button', name='Pergunta secreta', exact=True).click()
    expect(page.get_by_label('Pergunta secreta', exact=True)).to_have_value('pet')
    page.get_by_label('Pergunta secreta', exact=True).select_option('school')
    page.get_by_label('Resposta secreta', exact=True).fill('Escola Verde')
    page.get_by_label('Senha atual', exact=True).fill('senha-errada-000')
    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#recovery-setup-error')).to_contain_text('Senha atual incorreta')
    page.get_by_label('Senha atual', exact=True).fill(NEW_PASSWORD)
    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#recovery-setup')).to_have_count(0)
    page.locator('#logout').click()

    # Accounts created before this feature are asked to add a question once.
    old = uuid.uuid4().hex + '@example.org'
    store.register(old, 'Antigo', PASSWORD)
    login(page, old, PASSWORD)
    expect(page.locator('#recovery-setup')).to_be_visible()
    expect(page.locator('#recovery-setup')).to_contain_text('ainda não tem pergunta secreta')
    page.get_by_label('Pergunta secreta', exact=True).select_option('street')
    page.get_by_label('Resposta secreta', exact=True).fill('Rua das Flores')
    page.get_by_label('Senha atual', exact=True).fill(PASSWORD)
    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.locator('#recovery-setup')).to_have_count(0)
    assert page.request.post(base + '/api/recovery/question', headers={'Origin': base}, data={'email': old}).json()['question'] == 'street'
    assert not errors, errors
    print('PASS: cadastro com pergunta secreta, recuperação, nova senha, troca da pergunta e contas antigas', flush=True)


def main():
    with tempfile.TemporaryDirectory() as temp:
        store = PostgresStore(os.environ['TEST_DATABASE_URL']) if os.environ.get('TEST_DATABASE_URL') else Store(Path(temp) / 'recovery.sqlite')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                page.set_default_timeout(15000)
                exercise(page, f'http://127.0.0.1:{server.server_port}', store)
                browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
