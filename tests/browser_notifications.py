"""Explicit mention→recipient inbox→specific comment, read states and revoked access."""
import os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.store import Store
from server.workspace import Workspace
from server.app import handler_for

def exercise(owner,reader,base,a,b,item_id):
 for page,account in [(owner,a),(reader,b)]:assert page.request.post(base+'/api/login',data=account).ok
 owner.goto(base);owner.locator('[data-open]',has_text='Contrato compartilhado').click()
 def mention(text):
  owner.get_by_role('button',name='Comentários',exact=True).click()
  owner.get_by_label('Seu comentário',exact=True).fill(text)
  owner.get_by_label('Mencionar pessoas por e-mail',exact=True).fill(b['email'])
  owner.get_by_role('button',name='Enviar comentário',exact=True).click()
  expect(owner.locator('#modal')).to_contain_text('Mencionados: Nina')
  owner.get_by_role('button',name='Fechar',exact=True).click()
 mention('Primeira revisão pendente')
 reader.goto(base);expect(reader.locator('[data-notification-count]')).to_have_text('1')
 reader.locator('[data-nav=notifications]').click();expect(reader.locator('#notification-center article')).to_have_count(1)
 card=reader.locator('#notification-center article').first
 expect(card).to_contain_text('Primeira revisão pendente');expect(card).to_contain_text('Não lida')
 card.get_by_role('button',name='Marcar como lida',exact=True).click();expect(card).to_contain_text('Lida')
 card.get_by_role('button',name='Marcar como não lida',exact=True).click();expect(reader.locator('[data-notification-count]')).to_have_text('1')
 card.get_by_role('button',name='Ver comentário',exact=True).click()
 expect(reader.locator('#modal .comment-highlight')).to_contain_text('Primeira revisão pendente')
 expect(reader.locator('#comment-form')).to_have_count(0)
 reader.get_by_role('button',name='Fechar',exact=True).click()
 reader.locator('[data-nav=notifications]').click();expect(reader.get_by_role('button',name='Marcar como não lida',exact=True)).to_be_visible()
 mention('Segunda revisão');mention('Terceira revisão')
 reader.get_by_role('button',name='Atualizar notificações',exact=True).click();expect(reader.locator('#notification-center article')).to_have_count(3)
 reader.get_by_role('button',name='Marcar todas como lidas',exact=True).click();expect(reader.locator('[data-notification-count]')).to_be_hidden()
 reader.locator('#notification-center article').first.get_by_role('button',name='Excluir notificação',exact=True).click();expect(reader.locator('#notification-center article')).to_have_count(2)
 assert len(owner.request.get(base+'/api/items/'+item_id+'/comments').json()['items'])==3
 reader.set_viewport_size({'width':390,'height':844});assert reader.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
 assert owner.request.post(base+'/api/items/'+item_id+'/share',data={'email':b['email'],'role':'remove'}).ok
 reader.get_by_role('button',name='Atualizar notificações',exact=True).click();expect(reader.locator('#notification-center article')).to_have_count(0)
 expect(reader.locator('[data-notification-count]')).to_be_hidden()
 print('PASS: menção, central, abrir comentário, lida/não lida, exclusão individual, mobile e revogação',flush=True)

def main():
 with tempfile.TemporaryDirectory() as temp:
  store=Store(Path(temp)/'notify.sqlite');ws=Workspace(store)
  a={'email':'owner@example.org','name':'Ana','password':'long-test-password'};b={'email':'mentioned@example.org','name':'Nina','password':'long-test-password'}
  first=store.register(**a,question='pet',answer='Rex')['id'];store.register(**b,question='pet',answer='Rex')
  item=ws.create(first,{'kind':'document','title':'Contrato compartilhado','content':{'text':'Revisão'}});ws.share(first,item['id'],b['email'],'read')
  server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));owner=browser.new_page(viewport={'width':1440,'height':1000});reader=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    for page in [owner,reader]:page.on('pageerror',lambda e:errors.append(str(e)))
    exercise(owner,reader,f'http://127.0.0.1:{server.server_port}',a,b,item['id']);assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
