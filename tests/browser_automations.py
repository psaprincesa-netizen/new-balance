"""Public submission → project task, rule condition, execution log and replay safety."""
import os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.store import Store
from server.workspace import Workspace
from server.app import handler_for

def exercise(page,public,base,account,board_id,form_id):
    assert page.request.post(base+'/api/login',data=account).ok
    page.goto(base);page.locator('[data-open]',has_text='Pedidos automáticos').click()
    page.get_by_role('button',name='Automação de tarefas',exact=True).click()
    page.get_by_label('Criar tarefa a cada nova resposta pública',exact=True).check()
    page.get_by_label('Projeto de destino',exact=True).select_option(board_id)
    page.get_by_label('Texto usado no título',exact=True).select_option('1')
    page.get_by_label('Prefixo do título',exact=True).fill('Pedido: ')
    page.get_by_label('Condição da automação',exact=True).select_option('0')
    page.get_by_label('Resposta exigida para automação',exact=True).select_option('Sim')
    page.get_by_role('button',name='Salvar automação',exact=True).click()
    expect(page.locator('#notice')).to_contain_text('Automação salva')
    page.get_by_role('button',name='Fechar',exact=True).click()
    token=page.request.post(base+'/api/items/'+form_id+'/publication',data={'enabled':True}).json()['token']
    public.goto(base+'/?form='+token)
    public.locator('[name=q0]').select_option('Sim');public.locator('[name=q1]').fill('Entregar proposta')
    requests=[]
    public.on('request',lambda r:requests.append(r.post_data_json) if r.method=='POST' and '/api/forms/' in r.url else None)
    public.get_by_role('button',name='Enviar resposta',exact=True).click()
    expect(public.get_by_role('heading',name='Resposta enviada')).to_be_visible()
    assert len(requests)==1 and requests[0]['submission_id']
    replay=public.request.post(base+'/api/forms/'+token,data=requests[0]);assert replay.ok
    target=page.request.get(base+'/api/items/'+board_id).json()
    assert len(target['content']['tasks'])==1
    assert target['content']['tasks'][0]['title']=='Pedido: Entregar proposta'
    page.get_by_role('button',name='Automação de tarefas',exact=True).click()
    expect(page.locator('#automation-runs')).to_contain_text('Concluída')
    expect(page.locator('#automation-runs')).to_contain_text('Entregar proposta')
    page.get_by_role('button',name='Fechar',exact=True).click()
    public.goto(base+'/?form='+token);public.locator('[name=q0]').select_option('Não');public.locator('[name=q1]').fill('Sem tarefa')
    public.get_by_role('button',name='Enviar resposta',exact=True).click()
    expect(public.get_by_role('heading',name='Resposta enviada')).to_be_visible()
    assert len(page.request.get(base+'/api/items/'+board_id).json()['content']['tasks'])==1
    page.get_by_role('button',name='Conexões',exact=False).click()
    page.get_by_label('Formulário de origem',exact=True).select_option(form_id)
    expect(page.locator('#automation-runs')).to_contain_text('Ignorada')
    assert len(page.request.get(base+'/api/items/'+form_id).json()['content']['responses'])==2
    print('PASS: gatilho público, tarefa, condição, histórico de execução e reenvio sem duplicação',flush=True)

def main():
    with tempfile.TemporaryDirectory() as temp:
        store=Store(Path(temp)/'automations.sqlite');ws=Workspace(store)
        account={'email':'automation@example.org','name':'Ana','password':'long-test-password'}
        user=store.register(**account,question='pet',answer='Rex')['id']
        board=ws.create(user,{'kind':'board','title':'Projeto automatizado','content':{'tasks':[]}})
        form=ws.create(user,{'kind':'form','title':'Pedidos automáticos','content':{'questions':['Criar tarefa?','Pedido'],'fields':[{'type':'choice','required':True,'options':['Sim','Não']},{'type':'text','required':True,'options':[]}],'responses':[]}})
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'))
                page=browser.new_page(viewport={'width':1440,'height':1000});public=browser.new_page();errors=[]
                for target in [page,public]:target.on('pageerror',lambda e:errors.append(str(e)))
                exercise(page,public,f'http://127.0.0.1:{server.server_port}',account,board['id'],form['id'])
                assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
