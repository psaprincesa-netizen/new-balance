import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from server.store import Store,InvalidInput
from server.workspace import Workspace,Conflict


class PublicFormTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'db')
        self.ws=Workspace(self.store)
        self.user=self.store.register('owner@example.org','Owner','a-long-test-password')['id']
        self.other=self.store.register('other@example.org','Other','a-long-test-password')['id']
        self.item=self.ws.create(self.user,{'kind':'form','title':'Pesquisa','content':{'questions':['Seu contato','Escolha'],'fields':[{'type':'email','required':True,'options':[]},{'type':'choice','required':True,'options':['A','B']}],'responses':[]}})
        self.token=self.ws.publication(self.user,self.item['id'],True)['token']

    def test_public_collection_has_no_private_content_and_can_be_revoked(self):
        schema=self.ws.public_form(self.token)
        self.assertEqual(set(schema),{'title','questions','fields','schema_id','quiz'})
        self.ws.submit_form(self.token,['a@example.org','A'],schema['schema_id'])
        self.assertNotIn('responses',self.ws.public_form(self.token))
        with self.assertRaises(LookupError):self.ws.publication(self.other,self.item['id'],True)
        self.ws.share(self.user,self.item['id'],'other@example.org','read')
        with self.assertRaises(PermissionError):self.ws.publication(self.other,self.item['id'],True)
        self.ws.publication(self.user,self.item['id'],False)
        with self.assertRaises(LookupError):self.ws.public_form(self.token)
        with self.assertRaises(LookupError):self.ws.submit_form(self.token,['a@example.org','A'],schema['schema_id'])

    def test_invalid_answers_and_stale_question_schema_are_rejected(self):
        schema=self.ws.public_form(self.token)
        for answers in [['invalid','A'],['a@example.org','C'],['a@example.org'],['','A']]:
            with self.assertRaises(InvalidInput):self.ws.submit_form(self.token,answers,schema['schema_id'])
        with self.assertRaises(InvalidInput):self.ws.submit_form(self.token,['a@example.org','A'],'old-schema')
        self.assertEqual(self.ws.get(self.user,self.item['id'])['content']['responses'],[])

    def test_concurrent_responses_are_preserved_and_editor_conflicts(self):
        schema=self.ws.public_form(self.token)
        def submit(i):return self.ws.submit_form(self.token,[f'test{i}@example.org','A'],schema['schema_id'])
        with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(submit,range(6)))
        current=self.ws.get(self.user,self.item['id'])
        self.assertEqual(len(current['content']['responses']),6)
        self.assertEqual(current['version'],7)
        with self.assertRaises(Conflict):self.ws.update(self.user,self.item['id'],self.item)

    def test_quiz_private_key_and_server_scoring(self):
        content={'quiz':True,'questions':['Capital?','Avaliação','Comentário'],'fields':[{'type':'choice','required':True,'options':['Brasília','Recife'],'correctAnswer':'Brasília','points':5},{'type':'rating','required':True,'options':[]},{'type':'longtext','required':False,'options':[]}],'responses':[]}
        item=self.ws.create(self.user,{'kind':'form','title':'Quiz','content':content});token=self.ws.publication(self.user,item['id'],True)['token'];schema=self.ws.public_form(token)
        self.assertNotIn('correctAnswer',str(schema));self.assertNotIn('points',str(schema));self.ws.submit_form(token,['Brasília','5','Ótimo'],schema['schema_id'])
        result=self.ws.get(self.user,item['id'])['content']['responses'][0];self.assertEqual(result['score'],5);self.assertEqual(result['maxScore'],5)
        self.ws.submit_form(token,['Recife','4',''],schema['schema_id']);self.assertEqual(self.ws.get(self.user,item['id'])['content']['responses'][1]['score'],0)
        with self.assertRaises(InvalidInput):self.ws.submit_form(token,['Recife','6',''],schema['schema_id'])

class QuizFormTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'db')
        self.ws=Workspace(self.store)
        self.user=self.store.register('owner@example.org','Owner','a-long-test-password')['id']
        fields=[{'type':'choice','required':True,'options':['Brasília','Rio'],'correct':'Brasília','points':2},
                {'type':'multiple','required':True,'options':['2','3','4','5'],'correct':['2','3','5']},
                {'type':'scale','required':False,'options':[],'max':10},
                {'type':'text','required':False,'options':[],'correct':'São Paulo'}]
        self.item=self.ws.create(self.user,{'kind':'form','title':'Quiz','content':{'quiz':True,'questions':['Capital','Primos','Satisfação','Maior cidade'],'fields':fields,'responses':[]}})
        self.token=self.ws.publication(self.user,self.item['id'],True)['token']

    def test_public_schema_hides_the_answer_key_and_server_scores(self):
        schema=self.ws.public_form(self.token)
        self.assertTrue(schema['quiz'])
        self.assertTrue(all('correct' not in f and 'points' not in f for f in schema['fields']))
        result=self.ws.submit_form(self.token,['Brasília','5; 2; 3','9','sao  paulo'],schema['schema_id'])
        self.assertEqual((result['score'],result['total']),(4,4))
        result=self.ws.submit_form(self.token,['Rio','2; 3','',''],schema['schema_id'])
        self.assertEqual((result['score'],result['total']),(0,4))
        responses=self.ws.get(self.user,self.item['id'])['content']['responses']
        self.assertEqual([r['score'] for r in responses],[4,0])

    def test_new_answer_types_are_validated(self):
        schema=self.ws.public_form(self.token)
        for bad in (['Brasília','2; 7','',''],['Brasília','2; 2','',''],['Brasília','2','11','']):
            with self.assertRaises(InvalidInput):self.ws.submit_form(self.token,bad,schema['schema_id'])

    def test_invalid_quiz_definitions_are_rejected(self):
        content=self.ws.get(self.user,self.item['id'])['content']
        for change in ({'correct':['9']},{'options':['a;b'],'correct':[]},{'points':101},{'max':11}):
            broken={**content,'fields':[content['fields'][0],{**content['fields'][1],**change},*content['fields'][2:]]}
            with self.assertRaises(ValueError):
                self.ws.update(self.user,self.item['id'],{'title':'Quiz','content':broken,'version':1,'deleted':False})
