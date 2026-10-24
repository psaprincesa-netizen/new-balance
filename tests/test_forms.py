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
        self.assertEqual(set(schema),{'title','questions','fields','schema_id'})
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
