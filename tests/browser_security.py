"""Real-browser check of two-step verification and account activity. Requires Playwright and Chromium."""
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from server.app import handler_for
from server.store import Store, totp
from server.database import PostgresStore

PASSWORD = 'senha-longa-de-teste-123'


def login(page, email, password=PASSWORD):
    page.get_by_label('E-mail', exact=True).fill(email)
    page.get_by_label('Senha', exact=True).fill(password)
    page.get_by_role('button', name='Entrar no DRAP office', exact=False).click()


def exercise(page, base):
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    email = uuid.uuid4().hex + '@example.org'
    page.goto(base)
    page.get_by_role('button', name='Criar minha conta').click()
    page.get_by_label('Nome', exact=True).fill('Sara Teste')
    page.get_by_label('E-mail', exact=True).fill(email)
    page.get_by_label('Senha', exact=True).fill(PASSWORD)
    page.get_by_label('Pergunta secreta', exact=True).select_option(index=1)
    page.get_by_label('Resposta secreta', exact=True).fill('resposta de teste')
    page.get_by_role('button', name='Criar conta', exact=False).click()
    expect(page.get_by_role('heading', name='Olá, Sara. Vamos criar?')).to_be_visible()

    # Enable two-step verification with the QR code / key.
    page.get_by_role('button', name='Segurança da conta').click()
    expect(page.locator('#activity-list')).to_contain_text('Conta criada')
    page.get_by_role('button', name='Ativar verificação em duas etapas').click()
    page.get_by_label('Senha atual', exact=True).fill(PASSWORD)
    page.get_by_role('button', name='Continuar').click()
    expect(page.locator('.mfa-qr svg')).to_be_visible()
    secret = page.locator('#mfa-secret').inner_text().replace(' ', '')
    page.get_by_label('Código de 6 dígitos mostrado no app').fill(totp(secret, int(time.time()) // 30))
    page.get_by_role('button', name='Ativar', exact=True).click()
    expect(page.locator('#backup-codes li')).to_have_count(8)
    codes = page.locator('#backup-codes code').all_inner_texts()
    with page.expect_download() as download:
        page.get_by_role('button', name='Baixar códigos').click()
    assert codes[0] in Path(download.value.path()).read_text()
    page.get_by_role('button', name='Já guardei').click()
    expect(page.locator('#mfa-status')).to_contain_text('Ativa')
    expect(page.locator('#activity-list')).to_contain_text('Verificação em duas etapas ativada')
    page.get_by_role('button', name='Fechar').click()
    page.locator('#logout').click()

    # Login now asks for a code; a wrong code is refused, a backup code works once.
    login(page, email)
    expect(page.get_by_label('Código de verificação')).to_be_visible()
    page.get_by_label('Código de verificação').fill('000000' if totp(secret, int(time.time()) // 30) != '000000' else '111111')
    page.get_by_role('button', name='Entrar no DRAP office', exact=False).click()
    expect(page.locator('#auth-error')).to_contain_text('incorreto')
    page.get_by_label('Código de verificação').fill(codes[0])
    page.get_by_role('button', name='Entrar no DRAP office', exact=False).click()
    expect(page.get_by_role('heading', name='Olá, Sara. Vamos criar?')).to_be_visible()

    # Activity shows the failed code and the backup code; then disable with another backup code.
    page.get_by_role('button', name='Segurança da conta').click()
    expect(page.locator('#activity-list')).to_contain_text('Código de verificação incorreto')
    expect(page.locator('#activity-list')).to_contain_text('Código de backup usado')
    page.get_by_role('button', name='Desativar').click()
    page.get_by_label('Senha atual', exact=True).fill(PASSWORD)
    page.get_by_label('Código do app ou de backup').fill(codes[1])
    page.locator('#mfa-disable').get_by_role('button', name='Desativar').click()
    expect(page.locator('#mfa-status')).to_contain_text('Desativada')
    page.get_by_role('button', name='Fechar').click()
    page.locator('#logout').click()
    login(page, email)
    expect(page.get_by_role('heading', name='Olá, Sara. Vamos criar?')).to_be_visible()
    assert not errors, errors
    print('PASS: verificação em duas etapas com QR/chave, códigos de backup, login com código, desativação e atividade da conta', flush=True)


def main():
    with tempfile.TemporaryDirectory() as temp:
        store = PostgresStore(os.environ['TEST_DATABASE_URL']) if os.environ.get('TEST_DATABASE_URL') else Store(Path(temp) / 'security.sqlite')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                page = browser.new_page(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                page.set_default_timeout(15000)
                exercise(page, f'http://127.0.0.1:{server.server_port}')
                browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
