"""Installability, shortcut flow, mobile guidance, and a cache without private data."""
import os,tempfile,threading,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.app import handler_for
from server.store import Store

def exercise(page,base,check_offline=True,disconnect=None):
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(base+'/install');expect(page.locator('#install-title')).to_be_visible()
    page.evaluate('navigator.serviceWorker.ready.then(()=>true)');page.wait_for_function('navigator.serviceWorker.controller !== null')
    cdp=page.context.new_cdp_session(page)
    manifest=cdp.send('Page.getAppManifest');assert not manifest.get('errors'),manifest
    installability=cdp.send('Page.getInstallabilityErrors');assert not installability.get('installabilityErrors'),installability
    print('PASS: manifesto e critérios reais de instalação no Chromium',flush=True)
    # Exercise the user-confirmed browser event, including declining installation.
    page.evaluate('''() => {
      const event=new Event('beforeinstallprompt',{cancelable:true});
      event.prompt=async()=>{window.promptCount=(window.promptCount||0)+1;};
      event.userChoice=Promise.resolve({outcome:'dismissed'});window.dispatchEvent(event);
    }''')
    expect(page.locator('#install-now')).to_be_visible();page.locator('#install-now').click();expect(page.locator('#install-state')).to_contain_text('Instalação cancelada');assert page.evaluate('window.promptCount')==1;expect(page.locator('#install-now')).to_be_hidden()
    page.evaluate('''() => {
      const event=new Event('beforeinstallprompt',{cancelable:true});
      event.prompt=async()=>{window.promptCount++;};event.userChoice=Promise.resolve({outcome:'accepted'});window.dispatchEvent(event);
    }''')
    page.locator('#install-now').click();expect(page.locator('#install-state')).to_contain_text('Instalação solicitada');page.evaluate("window.dispatchEvent(new Event('appinstalled'))");expect(page.locator('#install-state')).to_contain_text('está instalado');expect(page.locator('#install-now')).to_be_hidden()
    assert page.locator('#install-url').input_value()==base+'/install'
    for width in [360,390,768,1440]:
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),width
    page.screenshot(path='/tmp/drap-install-desktop.png',full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path='/tmp/drap-install-mobile.png',full_page=True);page.set_viewport_size({'width':1440,'height':1000})
    page.locator('.source-download summary').click()
    with page.expect_download() as dl:page.get_by_role('link',name='Baixar código-fonte ZIP',exact=True).click()
    assert dl.value.suggested_filename=='drap-office.zip';assert dl.value.failure() is None
    # Register a disposable account, open a real editor, and retain unsaved work
    # while the browser shows the installation request from the toolbar.
    headers={'Origin':base};creds={'name':'Ana Install','email':uuid.uuid4().hex+'@example.org','password':uuid.uuid4().hex+'-Test12'}
    assert page.request.post(base+'/api/register',headers=headers,data={**creds,'question':'pet','answer':'resposta de teste'}).ok;assert page.request.post(base+'/api/login',headers=headers,data={**creds,'question':'pet','answer':'resposta de teste'}).ok
    response=page.request.post(base+'/api/items',headers=headers,data={'kind':'document','title':'Teste instalação','content':{'text':'Conteúdo privado'}});assert response.ok;item=response.json()
    page.goto(base);page.get_by_role('button',name='Teste instalação',exact=False).click();expect(page.locator('#preview')).to_have_attribute('data-ready','true');visual=page.get_by_role('textbox',name='Página do documento',exact=True);visual.fill('Edição ainda não salva')
    page.evaluate('''() => {const event=new Event('beforeinstallprompt',{cancelable:true});event.prompt=async()=>window.toolbarPrompt=true;event.userChoice=Promise.resolve({outcome:'dismissed'});window.dispatchEvent(event);}''')
    page.get_by_role('link',name='Instalar plataforma',exact=True).click();expect(visual).to_have_text('Edição ainda não salva');assert page.evaluate('window.toolbarPrompt');expect(page.locator('#save-state')).to_have_text('Alterações não salvas')
    with page.expect_popup() as popup:page.get_by_role('link',name='Instalar plataforma',exact=True).click()
    guide=popup.value;expect(guide.get_by_role('heading',name='Computador, tablet ou celular')).to_be_visible();guide.close();expect(visual).to_have_text('Edição ainda não salva')
    page.get_by_role('button',name='Salvar',exact=True).click();expect(page.locator('#save-state')).to_contain_text('Versão')
    cached=page.evaluate('''async()=>{const result=[];for(const name of await caches.keys()){if(name.startsWith('drap-offline-')){const cache=await caches.open(name);result.push(...(await cache.keys()).map(r=>new URL(r.url).pathname));}}return result;}''')
    assert cached==['/offline.html'],cached
    if check_offline:
        # Disconnect the test HTTP server as well: Chromium service workers
        # can still reach it when only the page context is marked offline.
        if disconnect:disconnect(True)
        page.context.set_offline(True);expect(page.locator('#connection-status')).to_contain_text('Sem conexão');expect(visual).to_have_text('Edição ainda não salva')
        assert page.evaluate("fetch('/api/items').then(()=>false).catch(()=>true)")
        response=page.goto(base+'/?offline-check=1');assert 'Você está sem conexão.' in response.text(),(response.status,response.text()[:300]);expect(page.get_by_role('heading',name='Você está sem conexão.')).to_be_visible();assert 'Conteúdo privado' not in page.locator('body').inner_text()
        if disconnect:disconnect(False)
        page.context.set_offline(False);page.get_by_role('link',name='Tentar novamente').click();expect(page.get_by_role('button',name='Teste instalação',exact=False)).to_be_visible()
    saved=page.request.get(base+'/api/items/'+item['id']).json();assert saved['content']['text']=='Edição ainda não salva'
    assert page.request.post(base+'/api/items/'+item['id'],headers=headers,data={**saved,'deleted':True}).ok
    assert not errors,errors
    print('PASS: instalação aceita/cancelada, atalho solicitado, editor preservado, download do código, layouts móveis e cache sem dados privados',flush=True)

def main():
    expect.set_options(timeout=30000)
    with tempfile.TemporaryDirectory() as tmp:
        disconnected=[False]
        class NetworkHandler(handler_for(Store(Path(tmp)/'test.sqlite'))):
            def do_GET(self):
                if disconnected[0]:
                    self.close_connection=True
                    return
                super().do_GET()
        server=ThreadingHTTPServer(('127.0.0.1',0),NetworkHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch_persistent_context(str(Path(tmp)/'browser'),headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),viewport={'width':1440,'height':1000});page=browser.new_page();page.set_default_timeout(30000)
                try:exercise(page,f'http://127.0.0.1:{server.server_port}',disconnect=lambda value:disconnected.__setitem__(0,value))
                finally:browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
