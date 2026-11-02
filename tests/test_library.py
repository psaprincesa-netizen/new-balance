"""Lightweight listings retain authorization, complete search and real totals."""
import json,unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_api
from server.store import Store
from server.workspace import Workspace

class LibraryTest(unittest.TestCase):
    setUp=test_api.ApiTest.setUp
    tearDown=test_api.ApiTest.tearDown
    request=test_api.ApiTest.request
    def account(self,email='library@example.org'):
        data={'email':email,'name':'Ana','password':'senha-longa-para-teste'}
        self.assertEqual(self.request('POST','/api/register',data)[0],201)
        status,user,cookie=self.request('POST','/api/login',data);self.assertEqual(status,200)
        return user['id'],{'Cookie':cookie.split(';')[0],'Content-Type':'application/json'}
    def test_metadata_pagination_and_bootstrap_avoid_document_contents(self):
        user,headers=self.account();ws=Workspace(Store(Path(self.tmp.name)/'db.sqlite'))
        for i in range(103):ws.create(user,{'kind':'document','title':f'Arquivo {i:03}','content':{'text':'conteúdo privado '*1000}})
        status,first,_=self.request('GET','/api/bootstrap',headers=headers)
        self.assertEqual(status,200);self.assertEqual(first['user']['id'],user);self.assertEqual(len(first['items']),100);self.assertEqual(first['next_offset'],100)
        self.assertLess(len(json.dumps(first)),40000);self.assertTrue(all('content' not in item for item in first['items']))
        status,last,_=self.request('GET','/api/library?offset=100',headers=headers)
        self.assertEqual(len(last['items']),3);self.assertIsNone(last['next_offset'])
        self.assertEqual(len({i['id'] for i in first['items']+last['items']}),103)
        item=first['items'][0];self.assertIn('content',self.request('GET','/api/items/'+item['id'],headers=headers)[1])
        self.assertIn('content',self.request('GET','/api/items',headers=headers)[1]['items'][0])
    def test_full_text_search_literals_and_revocation(self):
        owner,headers=self.account();reader,read_headers=self.account('reader@example.org');ws=Workspace(Store(Path(self.tmp.name)/'db.sqlite'))
        item=ws.create(owner,{'kind':'document','title':'Contrato','content':{'text':'agulha 50% a_b ÚNICO'}})
        ws.create(owner,{'kind':'note','title':'Outro','content':{'text':'sem o termo'}})
        self.assertEqual(self.request('GET','/api/library',headers=read_headers)[1]['items'],[])
        ws.share(owner,item['id'],'reader@example.org','read')
        for query in ['agulha','50%25','a_b','Documentos']:
            found=self.request('GET','/api/library?q='+query,headers=read_headers)[1]['items'];self.assertEqual([i['id'] for i in found],[item['id']]);self.assertEqual(found[0]['role'],'read')
        self.assertEqual(len(self.request('GET','/api/library?q=%25',headers=headers)[1]['items']),1)
        self.assertEqual(self.request('GET','/api/library?q='+'a'*201,headers=headers)[0],400)
        ws.share(owner,item['id'],'reader@example.org','remove')
        self.assertEqual(self.request('GET','/api/library?q=agulha',headers=read_headers)[1]['items'],[])
        self.assertEqual(self.request('GET','/api/items/'+item['id'],headers=read_headers)[0],404)
    def test_analytics_scope_and_no_anonymous_database_query(self):
        owner,headers=self.account();reader,read_headers=self.account('reader@example.org');store=Store(Path(self.tmp.name)/'db.sqlite');ws=Workspace(store)
        board=ws.create(owner,{'kind':'board','title':'Projeto','content':{'tasks':[{'title':'Feito','status':'Concluído','owner':'','due':''}]}})
        ws.create(owner,{'kind':'document','title':'Privado','content':{'text':'x'}})
        ws.share(owner,board['id'],'reader@example.org','read')
        self.assertEqual(self.request('GET','/api/analytics',headers=read_headers)[1],{'active':1,'tasks':1,'done':1,'responses':0,'by_kind':{'board':1}})
        ws.update(owner,board['id'],{**board,'deleted':True})
        self.assertEqual(self.request('GET','/api/analytics',headers=read_headers)[1]['active'],0)
        for path in ['/api/bootstrap','/api/library','/api/analytics']:
            self.assertEqual(self.request('GET',path)[0],401)
        with patch.object(store,'connect',side_effect=AssertionError('Unnecessary DB call')):self.assertIsNone(store.session_user(''))
