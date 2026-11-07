"""Dashboard CRUD, live refresh, grouped results, export, stale sources and mobile."""
import os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.store import Store
from server.workspace import Workspace
from server.app import handler_for

def exercise(page,base,account,source_id):
 assert page.request.post(base+'/api/login',data=account).ok
 page.goto(base);page.get_by_role('button',name='Indicadores',exact=False).click()
 page.get_by_role('button',name='Adicionar indicador',exact=True).click()
 page.get_by_label('Título do indicador',exact=True).fill('Vendas por equipe')
 page.get_by_label('Fonte do indicador',exact=True).select_option(source_id)
 page.get_by_label('Cálculo',exact=True).select_option('sum');page.get_by_label('Campo numérico',exact=True).select_option('1')
 page.get_by_label('Agrupar por',exact=True).select_option('0')
 page.get_by_role('button',name='Salvar indicador',exact=True).click()
 card=page.locator('#personal-dashboard article').filter(has=page.get_by_role('heading',name='Vendas por equipe',exact=True))
 expect(card.locator('tbody tr')).to_have_count(2);expect(card).to_contain_text('8');expect(card).to_contain_text('20')
 page.reload();page.get_by_role('button',name='Indicadores',exact=False).click();expect(card.locator('tbody tr')).to_have_count(2)
 page.get_by_role('button',name='Editar indicador Vendas por equipe',exact=True).click()
 page.get_by_label('Filtrar campo',exact=True).select_option('0');page.get_by_label('Valor exato do filtro',exact=True).fill('B')
 page.get_by_role('button',name='Salvar indicador',exact=True).click();expect(card.locator('tbody tr')).to_have_count(1);expect(card).to_contain_text('20')
 with page.expect_download() as download:page.get_by_role('button',name='Exportar indicadores CSV',exact=True).click()
 assert 'Vendas por equipe' in Path(download.value.path()).read_text(encoding='utf-8-sig')
 page.get_by_label('Nome do painel',exact=True).fill('Painel comercial');page.get_by_role('button',name='Renomear painel',exact=True).click()
 expect(page.locator('#personal-dashboard h2')).to_have_text('Painel comercial')
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(e=>({tag:e.tagName,id:e.id,class:e.className,width:e.getBoundingClientRect().width,text:e.innerText?.slice(0,80)}))")
 page.set_viewport_size({'width':1440,'height':1000})
 source=page.request.get(base+'/api/items/'+source_id).json();source['content']['rows'].append(['B','5'])
 assert page.request.post(base+'/api/items/'+source_id,data=source).ok
 page.get_by_role('button',name='Atualizar painel',exact=True).click();expect(card).to_contain_text('25')
 source=page.request.get(base+'/api/items/'+source_id).json();assert page.request.post(base+'/api/items/'+source_id,data=dict(source,deleted=True)).ok
 page.get_by_role('button',name='Atualizar painel',exact=True).click();expect(card).to_contain_text('Fonte indisponível ou sem acesso')
 page.get_by_role('button',name='Excluir indicador Vendas por equipe',exact=True).click();expect(page.locator('#personal-dashboard article')).to_have_count(0)
 print('PASS: BI configurável, filtro, persistência, exportação, atualização, exclusão e mobile',flush=True)

def main():
 with tempfile.TemporaryDirectory() as temp:
  store=Store(Path(temp)/'bi.sqlite');ws=Workspace(store)
  account={'email':'bi@example.org','name':'Ana','password':'long-test-password'}
  user=store.register(**account,question='pet',answer='Rex')['id']
  source=ws.create(user,{'kind':'table','title':'Vendas','content':{'columns':['Equipe','Valor'],'rows':[['A','10.5'],['A','-2.5'],['B','20']]}})
  server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'));page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    exercise(page,f'http://127.0.0.1:{server.server_port}',account,source['id']);assert not errors,errors;browser.close()
  finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
