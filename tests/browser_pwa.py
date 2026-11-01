"""Real-browser checks for the installable/offline app shell. Requires Playwright and Chromium."""
import json
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


def exercise(context, base):
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' and '401' not in msg.text and 'Failed to load resource' not in msg.text else None)

    manifest = page.request.get(base + '/manifest.webmanifest')
    assert manifest.ok and manifest.headers['content-type'].startswith('application/manifest+json')
    data = json.loads(manifest.text())
    assert data['name'] == 'DRAP office' and data['display'] == 'standalone' and data['start_url'] == '/'
    for icon in data['icons']:
        assert page.request.get(base + icon['src']).ok, icon['src']

    page.goto(base)
    assert page.evaluate("document.querySelector('link[rel=manifest]').href").endswith('/manifest.webmanifest')
    page.get_by_role('button', name='Criar minha conta').click()
    page.get_by_label('Nome', exact=True).fill('Pwa Teste')
    page.get_by_label('E-mail', exact=True).fill(uuid.uuid4().hex + '@example.org')
    page.get_by_label('Senha', exact=True).fill('senha-longa-de-teste-123')
    page.get_by_role('button', name='Criar conta', exact=False).click()
    expect(page.get_by_role('heading', name='Olá, Pwa. Vamos criar?')).to_be_visible()

    # Wait until the worker controls the page and the shell is cached.
    page.evaluate("navigator.serviceWorker.ready")
    page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=15000)
    cached = page.evaluate("caches.open('drap-shell-v1').then(c => c.keys()).then(k => k.map(r => new URL(r.url).pathname))")
    assert '/' in cached and '/app.js' in cached, cached
    assert not any(path.startswith('/api/') for path in cached), cached

    # Offline: the banner appears and a save keeps the edit as a local draft.
    page.get_by_role('button', name='＋ Criar novo').click()
    page.locator('#create-form select').select_option('document')
    page.get_by_label('Nome do arquivo', exact=True).last.fill('Documento PWA')
    page.get_by_role('button', name='Criar arquivo', exact=True).click()
    expect(page.locator('#title')).to_have_value('Documento PWA')
    context.set_offline(True)
    expect(page.locator('body.offline')).to_have_count(1)
    page.locator('#title').fill('Rascunho sem rede')
    page.keyboard.press('Control+s')
    expect(page.locator('#save-state')).to_contain_text('Sem conexão')
    drafts = page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('drap:draft:')).map(k => JSON.parse(localStorage.getItem(k)).title)")
    assert 'Rascunho sem rede' in drafts, drafts

    # Offline reload: the cached shell loads and explains the missing connection.
    page.reload()
    expect(page.get_by_text('Você está sem conexão.', exact=False)).to_be_visible()
    cached_api = page.evaluate("caches.open('drap-shell-v1').then(c => c.keys()).then(k => k.filter(r => new URL(r.url).pathname.startsWith('/api/')).length)")
    assert cached_api == 0

    # Back online: the page reopens on its own.
    context.set_offline(False)
    expect(page.get_by_role('heading', name='Olá, Pwa. Vamos criar?')).to_be_visible(timeout=15000)
    assert not errors, errors
    print('PASS: manifesto, ícones, service worker, aviso offline, rascunho e reabertura', flush=True)


def main():
    with tempfile.TemporaryDirectory() as temp:
        store = PostgresStore(os.environ['TEST_DATABASE_URL']) if os.environ.get('TEST_DATABASE_URL') else Store(Path(temp) / 'pwa.sqlite')
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'))
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                context.set_default_timeout(15000)
                exercise(context, f'http://127.0.0.1:{server.server_port}')
                browser.close()
        finally:
            server.shutdown()


if __name__ == '__main__':
    main()
