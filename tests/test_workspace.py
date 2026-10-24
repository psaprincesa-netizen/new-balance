import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from server.store import Store, InvalidInput
from server.workspace import Workspace, Conflict


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = Store(Path(tmp.name) / 'test.sqlite')
        self.workspace = Workspace(self.store)
        self.a = self.store.register('a@example.org', 'Ana', 'a-long-test-password')['id']
        self.b = self.store.register('b@example.org', 'Bia', 'another-test-password')['id']
        self.item = self.workspace.create(self.a, {'kind':'document','title':'Projeto','content':{'text':'original'}})

    def payload(self, text='nova versão', **kwargs):
        return {'title':'Projeto','content':{'text':text},'version':self.item['version'], **kwargs}

    def test_isolation_sharing_read_edit_revoke(self):
        self.assertEqual(self.workspace.list(self.b), [])
        with self.assertRaises(LookupError):
            self.workspace.get(self.b, self.item['id'])
        with self.assertRaises(LookupError):
            self.workspace.history(self.b, self.item['id'])
        with self.assertRaises(LookupError):
            self.workspace.update(self.b, self.item['id'], self.payload())
        self.workspace.share(self.a, self.item['id'], 'b@example.org', 'read')
        self.assertEqual(self.workspace.get(self.b, self.item['id'])['role'], 'read')
        with self.assertRaises(PermissionError):
            self.workspace.update(self.b, self.item['id'], self.payload())
        with self.assertRaises(PermissionError):
            self.workspace.share(self.b, self.item['id'], 'a@example.org', 'edit')
        self.workspace.share(self.a, self.item['id'], 'b@example.org', 'edit')
        self.assertEqual(self.workspace.update(self.b, self.item['id'], self.payload())['version'], 2)
        self.workspace.share(self.a, self.item['id'], 'b@example.org', 'remove')
        self.assertEqual(self.workspace.list(self.b), [])

    def test_versions_trash_restore_and_reopen(self):
        self.item = self.workspace.update(self.a, self.item['id'], self.payload())
        self.item = self.workspace.update(self.a, self.item['id'], self.payload(deleted=True))
        self.assertTrue(self.item['deleted'])
        original = self.workspace.history(self.a, self.item['id'])[-1]
        restored = self.workspace.update(self.a, self.item['id'], self.payload(original['content']['text']))
        self.assertFalse(restored['deleted'])
        self.assertEqual(restored['version'], 4)
        self.assertEqual(Workspace(self.store).get(self.a, self.item['id'])['content']['text'], 'original')

    def test_real_concurrent_updates_do_not_overwrite(self):
        def update(text):
            try:
                return self.workspace.update(self.a, self.item['id'], self.payload(text))['content']['text']
            except Conflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(update, ['one','two']))
        self.assertEqual(results.count('conflict'), 1)
        self.assertEqual(len(self.workspace.history(self.a, self.item['id'])), 2)

    def test_editor_contracts(self):
        valid = {'document':{'text':'a'},'note':{'text':'b'},'sheet':{'cells':[['1','=A1*2']]},
                 'slides':{'slides':[{'title':'a','body':'b','notes':''}]},'board':{'tasks':[]},
                 'calendar':{'events':[]},'form':{'questions':[],'responses':[]},
                 'table':{'columns':['Nome'],'rows':[['Ana']]},'diagram':{'nodes':['Início']},
                 'portal':{'text':'Portal','links':[]}}
        for kind, content in valid.items():
            item = self.workspace.create(self.a, {'kind':kind,'title':kind,'content':content})
            self.assertEqual(item['content'], content)
            with self.assertRaises(InvalidInput):
                self.workspace.create(self.a, {'kind':kind,'title':kind,'content':{'invalid':True}})
        with self.assertRaises(InvalidInput):
            self.workspace.create(self.a, {'kind':'sheet','title':'bad','content':{'cells':[['1'],['2','3']]}})

    def test_comments_and_share_list_respect_permissions(self):
        item=self.item['id']
        self.workspace.comment(self.a,item,'Revisar o conteúdo')
        self.assertEqual(self.workspace.comments(self.a,item)[0]['body'],'Revisar o conteúdo')
        with self.assertRaises(LookupError):self.workspace.comments(self.b,item)
        self.workspace.share(self.a,item,'b@example.org','read')
        self.assertEqual(self.workspace.shares(self.a,item)[0]['email'],'b@example.org')
        self.assertEqual(len(self.workspace.comments(self.b,item)),1)
        with self.assertRaises(PermissionError):self.workspace.comment(self.b,item,'Não permitido')
        with self.assertRaises(PermissionError):self.workspace.shares(self.b,item)
        self.workspace.share(self.a,item,'b@example.org','edit')
        self.workspace.comment(self.b,item,'Concluído')
        self.assertEqual(len(self.workspace.comments(self.a,item)),2)
        self.workspace.share(self.a,item,'b@example.org','remove')
        with self.assertRaises(LookupError):self.workspace.comments(self.b,item)
