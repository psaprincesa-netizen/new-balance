"""Create, execute, reopen, inspect, trash and restore a scheduled task rule."""
import os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from datetime import datetime,timezone,timedelta
from playwright.sync_api import sync_playwright,expect
from server.store import Store
from server.workspace import Workspace
from server.app import handler_for

def exercise(page,base,account,board_id):
 assert page.request.post(base+'/api/login',data=account).ok
 page.goto(base);page.locator('[data-nav=automation]').click()
 page.get_by_role('button',name='Novo agendamento',exact=True).click()
 page.get_by_label('Nome do agendamento',exact=True).fill('Revisão agendada')
 page.get_by_label('Projeto do agendamento',exact=True).select_option(board_id)
 page.get_by_label('Título da tarefa agendada',exact=True).fill('Revisar contrato')
 page.get_by_label('Primeira data',exact=True).fill(datetime.now(timezone.utc).date().isoformat())
 page.get_by_label('Fuso do agendamento',exact=True).fill('UTC')
 page.get_by_label('Prazo após a ocorrência (dias)',exact=True).fill('2')
 page.get_by_role('button',name='Salvar agendamento',exact=True).click()
 card=page.locator('[data-schedule]').filter(has=page.get_by_role('heading',name='Revisão agendada',exact=True))
 expect(card).to_contain_text('Ativo')
 card.get_by_role('button',name='Processar este agendamento',exact=True).click();expect(card).to_contain_text('Concluído')
 card.get_by_role('button',name='Histórico de execuções',exact=True).click();expect(card.locator('.schedule-history')).to_contain_text('Concluída')
 tasks=page.request.get(base+'/api/items/'+board_id).json()['content']['tasks'];assert len(tasks)==1 and tasks[0]['title']=='Revisar contrato'
 assert tasks[0]['due']==(datetime.now(timezone.utc).date()+timedelta(days=2)).isoformat()
 card.get_by_role('button',name='Processar este agendamento',exact=True).click()
 expect(page.locator('#schedule-status')).to_contain_text('0 ocorrência')
 assert len(page.request.get(base+'/api/items/'+board_id).json()['content']['tasks'])==1
 page.reload();page.locator('[data-nav=automation]').click();expect(card).to_contain_text('Concluído')
 page.get_by_role('button',name='Atualizar agendamentos',exact=True).click();expect(card).to_contain_text('Concluído')
 card.get_by_role('button',name='Excluir agendamento',exact=True).click();expect(page.locator('[data-schedule]')).to_have_count(0)
 page.get_by_role('button',name='Ver lixeira de agendamentos',exact=True).click();expect(card).to_be_visible()
 card.get_by_role('button',name='Restaurar agendamento',exact=True).click();expect(page.locator('[data-schedule]')).to_have_count(0)
 page.get_by_role('button',name='Ver agendamentos',exact=True).click();expect(card).to_contain_text('Pausado')
 page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
 print('PASS: agendamento, execução, prazo, histórico, idempotência, reabertura, lixeira/restauração e mobile',flush=True)

def main():
 with tempfile.TemporaryDirectory() as temp:
  store=Store(Path(temp)/'schedule.sqlite');ws=Workspace(store);account={'email':'scheduler@example.org','name':'Ana','password':'long-test-password'}
  user=store.register(**account,question='pet',answer='Rex')['id'];board=ws.create(user,{'kind':'board','title':'Projeto agendado','content':{'tasks':[]}})
  server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    exercise(page,f'http://127.0.0.1:{server.server_port}',account,board['id']);assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
