import io,json,os,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from server.ai_assistant import assist,AssistantError,context_text,reserve_request
from server.store import Store,InvalidInput
from server.workspace import Workspace
from tests import test_api

class AssistantTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=Store(Path(tmp.name)/'ai.sqlite');self.ws=Workspace(self.store)
        self.user=self.store.register('ai@example.org','Ana','long-test-password')['id']
        self.other=self.store.register('other@example.org','Bia','long-test-password')['id']
        self.item=self.ws.create(self.user,{'kind':'document','title':'Plano','content':{'text':'Entrega na sexta.'}})
        self.env=patch.dict(os.environ,{'AI_GATEWAY_API_KEY':'synthetic-token','AI_DAILY_USER_LIMIT':'20','AI_DAILY_PROJECT_LIMIT':'200'})
        self.env.start();self.addCleanup(self.env.stop)
        self.payload={'action':'summarize','prompt':'Em uma frase','item_id':self.item['id'],'consent':True}

    def test_provider_payload_and_result_do_not_write_source(self):
        def provider(request,**kwargs):
            data=json.loads(request.data)
            self.assertTrue(data['model'].startswith('google/gemini-'))
            self.assertIn('Entrega na sexta.',data['messages'][1]['content'])
            self.assertEqual(request.headers['Authorization'],'Bearer synthetic-token')
            self.assertLessEqual(kwargs['timeout'],18)
            return io.BytesIO(json.dumps({'choices':[{'message':{'content':'Resumo'},'finish_reason':'stop'}]}).encode())
        result=assist(self.ws,self.user,self.payload,opener=provider)
        self.assertEqual(result['text'],'Resumo');self.assertEqual(self.ws.get(self.user,self.item['id'])['version'],1)
        self.assertEqual(len(self.ws.list(self.user)),1)

    def test_access_and_consent_fail_before_network(self):
        def never(*a,**k):self.fail('Provider must not be called')
        with self.assertRaises(LookupError):assist(self.ws,self.other,self.payload,opener=never)
        with self.assertRaises(InvalidInput):assist(self.ws,self.user,dict(self.payload,consent=False),opener=never)
        with patch.dict(os.environ,{'AI_GATEWAY_API_KEY':'','VERCEL_OIDC_TOKEN':''}):
            with self.assertRaises(AssistantError):assist(self.ws,self.user,self.payload,opener=never)

    def test_errors_are_sanitized(self):
        def provider(*a,**k):raise HTTPError('https://secret.invalid',403,'SECRET',{},io.BytesIO(b'SECRET'))
        with self.assertRaises(AssistantError) as result:assist(self.ws,self.user,self.payload,opener=provider)
        self.assertNotIn('SECRET',str(result.exception))
        def invalid(*a,**k):return io.BytesIO(b'{"choices":[]}')
        with self.assertRaises(AssistantError):assist(self.ws,self.user,self.payload,opener=invalid)

    def test_gateway_verification_error_has_actionable_message(self):
        def provider(*a,**k):raise HTTPError('https://gateway.invalid',403,'Forbidden',{},io.BytesIO(b'{"error":{"type":"customer_verification_required"}}'))
        with self.assertRaises(AssistantError) as result:assist(self.ws,self.user,self.payload,opener=provider)
        self.assertIn('forma de pagamento',str(result.exception))

    def test_context_excludes_binary_and_quiz_answers_and_marks_truncation(self):
        text,truncated=context_text(dict(self.item,content={'text':'a'*25000,'images':[{'data':'secret-binary'}]}))
        self.assertEqual(len(text),24000);self.assertTrue(truncated);self.assertNotIn('secret-binary',text)
        text,_=context_text({'kind':'form','content':{'questions':['Q'],'responses':[{'answers':['PRIVATE']}],'fields':[{'correct':'SECRET'}]}})
        self.assertNotIn('SECRET',text);self.assertNotIn('PRIVATE',text)

    def test_runtime_oidc_is_resolved_per_request(self):
        from server.ai_assistant import status
        with patch.dict(os.environ,{'AI_GATEWAY_API_KEY':'','VERCEL_OIDC_TOKEN':''}):
            self.assertFalse(status()['configured'])
            self.assertTrue(status('synthetic-runtime-token')['configured'])
        self.assertNotIn('synthetic-runtime-token',json.dumps(status()))

    def test_atomic_budget_is_not_exceeded(self):
        with patch.dict(os.environ,{'AI_DAILY_USER_LIMIT':'2'}):
            def attempt(_):
                try:reserve_request(self.store,self.user);return 'ok'
                except AssistantError:return 'limited'
            with ThreadPoolExecutor(max_workers=4) as executor:results=list(executor.map(attempt,range(4)))
        self.assertEqual(results.count('ok'),2)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT attempts FROM ai_daily WHERE key='global'").fetchone()['attempts'],2)

class AssistantApiTest(unittest.TestCase):
    setUp=test_api.ApiTest.setUp
    tearDown=test_api.ApiTest.tearDown
    request=test_api.ApiTest.request

    def test_authenticated_status_origin_and_generation(self):
        self.assertEqual(self.request('GET','/api/ai/status')[0],401)
        self.assertEqual(self.request('POST','/api/ai',{})[0],401)
        account={'email':'api-ai@example.org','name':'Ana','password':'long-test-password','question':'pet','answer':'Rex'}
        self.request('POST','/api/register',account)
        cookie=self.request('POST','/api/login',account)[2].split(';')[0]
        headers={'Cookie':cookie,'Content-Type':'application/json'}
        self.assertEqual(self.request('GET','/api/ai/status',headers=headers)[0],200)
        with patch('server.ai_assistant.assist',return_value={'text':'Test result'}) as generate:
            self.assertEqual(self.request('POST','/api/ai',{'consent':True},headers)[1]['text'],'Test result')
            self.assertEqual(self.request('POST','/api/ai',{},dict(headers,Origin='https://other.invalid'))[0],403)
            self.assertEqual(generate.call_count,1)
