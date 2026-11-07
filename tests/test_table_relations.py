import tempfile,unittest
from pathlib import Path
from server.store import Store,InvalidInput
from server.workspace import Workspace,Conflict
from server.table_relations import related_records
class RelationTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=Store(Path(tmp.name)/'relations.sqlite');self.ws=Workspace(self.store)
        self.a=self.store.register('a@example.org','Ana','long-test-password')['id']
        self.b=self.store.register('b@example.org','Bia','long-test-password')['id']
        self.target=self.ws.create(self.a,{'kind':'table','title':'Pedidos','content':{'columns':['Cliente','Pedido'],'rows':[['A','P1'],['A','P2'],['B','P3'],['','Vazio']]}})
        self.relation={'id':'r1','name':'Pedidos do cliente','sourceColumn':0,'sourceName':'Código','targetId':self.target['id'],'targetColumn':0,'targetName':'Cliente'}
        self.source=self.ws.create(self.a,{'kind':'table','title':'Clientes','content':{'columns':['Código'],'rows':[['A'],['B'],['']], 'relations':[self.relation]}})
    def query(self,user=None,row=0,version=1,offset=0):
        return related_records(self.ws,user or self.a,self.source['id'],'r1',row,version,offset)
    def test_matching_persistence_and_blank_keys(self):
        self.assertEqual(self.query()['rows'],[['A','P1'],['A','P2']])
        self.assertEqual(self.query(row=1)['total'],1)
        self.assertEqual(self.query(row=2)['rows'],[])
        self.assertEqual(Workspace(self.store).get(self.a,self.source['id'])['content']['relations'],[self.relation])
    def test_both_permissions_are_required_and_revocation_is_immediate(self):
        with self.assertRaises(LookupError):self.query(self.b)
        self.ws.share(self.a,self.source['id'],'b@example.org','read')
        with self.assertRaises(LookupError):self.query(self.b)
        self.ws.share(self.a,self.target['id'],'b@example.org','read')
        self.assertEqual(self.query(self.b)['total'],2)
        self.ws.share(self.a,self.target['id'],'b@example.org','remove')
        with self.assertRaises(LookupError):self.query(self.b)
    def test_versions_and_target_schema_changes_do_not_match_wrong_columns(self):
        with self.assertRaises(Conflict):self.query(version=2)
        data=dict(self.target,content={'columns':['Renomeado','Pedido'],'rows':[['A','P1']]})
        self.ws.update(self.a,self.target['id'],data)
        with self.assertRaises(Conflict):self.query()
    def test_ambiguous_destination_column_is_rejected(self):
        data=dict(self.target,content={'columns':['Cliente','Cliente'],'rows':[['A','Outro']]})
        self.ws.update(self.a,self.target['id'],data)
        with self.assertRaises(Conflict):self.query()

    def test_invalid_config_and_pagination(self):
        for change in [{'sourceColumn':True},{'sourceColumn':3},{'sourceName':'Outro'},{'targetColumn':26}]:
            with self.assertRaises(InvalidInput):self.ws.create(self.a,{'kind':'table','title':'Inválido','content':dict(self.source['content'],relations=[dict(self.relation,**change)])})
        data=dict(self.target,content={'columns':['Cliente','Pedido'],'rows':[['A',str(i)] for i in range(120)]})
        self.ws.update(self.a,self.target['id'],data)
        result=self.query();self.assertEqual(len(result['rows']),50);self.assertEqual(result['next_offset'],50)
        self.assertEqual(len(self.query(offset=100)['rows']),20)
        with self.assertRaises(InvalidInput):self.query(row=99)
