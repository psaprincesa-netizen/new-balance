"""Owner approval/rejection UI, persistence and public submission semantics."""
import os,tempfile,threading,uuid
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.store import Store
from server.workspace import Workspace
from server.app import handler_for

def exercise(page,public,base,account,board_id,form_id):
 assert page.request.post(base+'/api/login',data=account).ok
 page.goto(base);page.locator('[data-open]',has_text='Pedidos para aprovação').click()
 page.get_by_role('button',name='Automação de tarefas',exact=True).click()
 page.get_by_label('Criar tarefa a cada nova resposta pública',exact=True).check()
 page.get_by_label('Exigir minha aprovação antes de criar a tarefa',exact=True).check()
 page.get_by_label('Projeto de destino',exact=True).select_option(board_id)
 page.get_by_label('Texto usado no título',exact=True).select_option('0')
 page.get_by_label('Prefixo do título',exact=True).fill('Pedido: ')
 page.get_by_role('button',name='Salvar automação',exact=True).click();expect(page.locator('#notice')).to_contain_text('Automação salva')
 token=page.request.post(base+'/api/items/'+form_id+'/publication',data={'enabled':True}).json()['token']
 def send(title):
  public.goto(base+'/?form='+token)
  public.locator('[name=q0]').fill(title);public.get_by_role('button',name='Enviar resposta',exact=True).click()
  expect(public.get_by_role('heading',name='Resposta enviada')).to_be_visible()
 send('Revisar proposta')
 page.get_by_role('button',name='Atualizar painel',exact=True).click()
 card=page.locator('#automation-runs article').filter(has_text='Pedido: Revisar proposta')
 expect(card).to_contain_text('Aguardando aprovação');expect(card).to_contain_text('Projeto para aprovação')
 card.get_by_role('button',name='Ver resposta original',exact=True).click();expect(card.locator('dd')).to_have_text('Revisar proposta')
 assert not page.request.get(base+'/api/items/'+board_id).json()['content']['tasks']
 page.get_by_role('button',name='Fechar',exact=True).click();page.reload();page.locator('[data-open]',has_text='Pedidos para aprovação').click()
 page.get_by_role('button',name='Automação de tarefas',exact=True).click()
 expect(page.get_by_label('Exigir minha aprovação antes de criar a tarefa',exact=True)).to_be_checked()
 expect(card).to_contain_text('Aguardando aprovação')
 card.get_by_role('button',name='Aprovar e criar tarefa',exact=True).click();expect(card).to_contain_text('Concluída');expect(card).to_contain_text('Decisão: aprovada')
 tasks=page.request.get(base+'/api/items/'+board_id).json()['content']['tasks'];assert len(tasks)==1 and tasks[0]['title']=='Pedido: Revisar proposta'
 send('Não executar');page.get_by_role('button',name='Atualizar painel',exact=True).click()
 rejected=page.locator('#automation-runs article').filter(has_text='Pedido: Não executar')
 rejected.get_by_role('button',name='Rejeitar execução',exact=True).click();expect(rejected).to_contain_text('Rejeitada');expect(rejected).to_contain_text('Decisão: rejeitada')
 assert len(page.request.get(base+'/api/items/'+board_id).json()['content']['tasks'])==1
 expect(rejected.get_by_role('button',name='Reprocessar execução',exact=True)).to_have_count(0)
 print('PASS: aprovação, rejeição, persistência, histórico e tarefa após decisão',flush=True)

def main():
 with tempfile.TemporaryDirectory() as temp:
  store=Store(Path(temp)/'approval.sqlite');ws=Workspace(store);account={'email':'approve@example.org','name':'Ana','password':'long-test-password'}
  user=store.register(**account,question='pet',answer='Rex')['id']
  board=ws.create(user,{'kind':'board','title':'Projeto para aprovação','content':{'tasks':[]}})
  form=ws.create(user,{'kind':'form','title':'Pedidos para aprovação','content':{'questions':['Pedido'],'fields':[{'type':'text','required':True,'options':[]}],'responses':[]}})
  server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));page=browser.new_page(viewport={'width':1440,'height':1000});public=browser.new_page();errors=[]
    for target in [page,public]:target.on('pageerror',lambda e:errors.append(str(e)))
    exercise(page,public,f'http://127.0.0.1:{server.server_port}',account,board['id'],form['id']);assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
