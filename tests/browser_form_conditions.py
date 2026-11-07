"""Configure conditional questions and exercise public chains, clearing and quiz grading."""
import os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from server.store import Store
from server.workspace import Workspace
from server.app import handler_for

def content():
    return {'questions':['Atender?','Categoria','Detalhes'],'responses':[],'quiz':True,'fields':[
        {'type':'choice','required':True,'options':['Sim','Não']},
        {'type':'choice','required':True,'options':['A','B'],'correct':'A','points':5},
        {'type':'text','required':True,'options':[],'correct':'ok','points':10,'showWhen':{'question':1,'value':'A'}}]}

def exercise_owner(page,base,account):
    assert page.request.post(base+'/api/login',data=account).ok
    page.goto(base);page.locator('[data-open]',has_text='Formulário condicional').click()
    page.get_by_role('button',name='Exibição da pergunta 2',exact=True).click()
    page.get_by_label('Pergunta anterior',exact=True).select_option('0')
    page.get_by_label('Resposta de exibição',exact=True).select_option('Sim')
    page.get_by_role('button',name='Aplicar regra',exact=True).click()
    page.get_by_role('button',name='Salvar',exact=True).click()
    expect(page.locator('#save-state')).to_contain_text('Versão 2')

def exercise_public(page,base,token):
    page.goto(base+'/?form='+token)
    form=page.locator('#public-response')
    expect(form.locator('[data-answer="1"]')).to_be_hidden()
    expect(form.locator('[data-answer="2"]')).to_be_hidden()
    form.locator('[name=q0]').select_option('Não')
    page.get_by_role('button',name='Enviar resposta',exact=True).click()
    expect(page.get_by_role('heading',name='Resposta enviada')).to_be_visible()
    page.goto(base+'/?form='+token)
    form.locator('[name=q0]').select_option('Sim');form.locator('[name=q1]').select_option('A')
    form.locator('[name=q2]').fill('Rascunho a limpar')
    form.locator('[name=q0]').select_option('Não')
    expect(form.locator('[name=q1]')).to_be_disabled();expect(form.locator('[name=q2]')).to_have_value('')
    form.locator('[name=q0]').select_option('Sim')
    expect(form.locator('[name=q1]')).to_have_value('')
    form.locator('[name=q1]').select_option('A');form.locator('[name=q2]').fill('ok')
    page.get_by_role('button',name='Enviar resposta',exact=True).click()
    expect(page.locator('#quiz-score')).to_have_text('Sua nota: 15 de 15')
    print('PASS: ramificação pública, campos ocultos não obrigatórios, limpeza em cadeia e nota',flush=True)

def main():
    with tempfile.TemporaryDirectory() as temp:
        store=Store(Path(temp)/'conditions.sqlite');ws=Workspace(store)
        account={'email':'conditional@example.org','name':'Ana','password':'long-test-password'}
        user=store.register(**account,question='pet',answer='Rex')['id']
        item=ws.create(user,{'kind':'form','title':'Formulário condicional','content':content()})
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(store));threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'))
                owner=browser.new_page();errors=[];owner.on('pageerror',lambda error:errors.append(str(error)))
                exercise_owner(owner,base,account)
                token=ws.publication(user,item['id'],True)['token']
                public=browser.new_page();public.on('pageerror',lambda error:errors.append(str(error)))
                exercise_public(public,base,token)
                responses=ws.get(user,item['id'])['content']['responses']
                assert responses[0]['answers']==['Não','','']
                assert responses[1]['score']==15 and responses[1]['total']==15
                assert not errors,errors;browser.close()
        finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
