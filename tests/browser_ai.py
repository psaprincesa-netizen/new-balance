"""Browser → authenticated API → synthetic provider → preview → private document."""
import io,json,os,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from playwright.sync_api import sync_playwright,expect
from server.app import handler_for
from server.store import Store
from tests.browser_projects import signup


def main():
    sent=[]
    def provider(request,**kwargs):
        data=json.loads(request.data);sent.append(data)
        assert 'Plano sintético' in data['messages'][1]['content']
        return io.BytesIO(json.dumps({'choices':[{'message':{'content':'Resumo sintético aprovado.'},'finish_reason':'stop'}]}).encode())
    with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{'AI_GATEWAY_API_KEY':'synthetic-token'}), patch('server.ai_assistant.urlopen',side_effect=provider):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(Store(Path(temp)/'ai.sqlite')))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'))
                page=browser.new_page(viewport={'width':1280,'height':1000});errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                signup(page,f'http://127.0.0.1:{server.server_port}')
                item=page.evaluate("""async()=>{const r=await fetch('/api/items',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:'document',title:'Plano sintético',content:{text:'Entrega em dezembro.'}})});return r.json();}""")
                page.reload()
                page.get_by_role('button',name='Gemini',exact=False).click()
                page.get_by_label('Ação do Gemini').select_option('summarize')
                page.get_by_label('Arquivo salvo para contexto').select_option(item['id'])
                page.get_by_label('Instruções para o Gemini').fill('Faça um resumo.')
                page.get_by_role('button',name='Executar com Gemini').click()
                assert len(sent)==0 # Native required consent blocks sending.
                page.locator('input[name=consent]').check()
                page.get_by_role('button',name='Executar com Gemini').click()
                expect(page.get_by_label('Texto gerado')).to_have_value('Resumo sintético aprovado.')
                assert len(sent)==1
                page.get_by_role('button',name='Salvar como novo documento').click()
                expect(page.get_by_label('Nome do arquivo',exact=True)).to_have_value('Resultado do Gemini')
                page.get_by_role('button',name='←',exact=True).click()
                expect(page.locator('[data-open]').filter(has_text='Plano sintético').first).to_be_visible()
                assert not errors,errors
                browser.close()
                print('PASS: consentimento, API autenticada, contexto, resultado Gemini sintético e novo documento privado')
        finally:server.shutdown();server.server_close()

if __name__=='__main__':main()
