import tempfile,unittest
from pathlib import Path
from server.store import Store,InvalidInput
from server.workspace import Workspace,Conflict
from server.dashboards import get,save,sources

class DashboardTest(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.store=Store(Path(tmp.name)/'test.sqlite');self.ws=Workspace(self.store)
  self.a=self.store.register('a@example.org','Ana','long-test-password')['id'];self.b=self.store.register('b@example.org','Bia','long-test-password')['id']
  self.table=self.ws.create(self.a,{'kind':'table','title':'Vendas','content':{'columns':['Equipe','Valor'],'rows':[['A','10.5'],['A','-2.5'],['B','20'],['B','']]}})
 def widget(self,**changes):return dict({'id':'w1','title':'Vendas','sourceId':self.table['id'],'operation':'sum','valueField':{'index':1,'name':'Valor'},'groupField':None,'filter':None},**changes)
 def save(self,widgets,version=0):return save(self.ws,self.a,{'version':version,'config':{'title':'Meu BI','widgets':widgets}})
 def test_aggregates_filter_empty_and_live_update(self):
  self.save([self.widget(),self.widget(id='avg',operation='average'),self.widget(id='group',groupField={'index':0,'name':'Equipe'}),self.widget(id='count',operation='count',valueField=None,filter={'field':{'index':0,'name':'Equipe'},'value':'B'})])
  result=get(self.ws,self.a)['results'];self.assertEqual(result[0]['value'],28);self.assertAlmostEqual(result[1]['value'],28/3)
  self.assertEqual(result[2]['groups'],[{'label':'A','value':8.0},{'label':'B','value':20.0}]);self.assertEqual(result[3]['value'],2)
  self.ws.update(self.a,self.table['id'],dict(self.table,content={'columns':['Equipe','Valor'],'rows':[['A','100']]}))
  result=get(self.ws,self.a)['results'];self.assertEqual(result[0]['value'],100);self.assertEqual(result[0]['sourceVersion'],2)
  self.assertEqual(result[3]['value'],0)
  self.assertEqual(get(Workspace(self.store),self.a)['config']['title'],'Meu BI')
 def test_permission_revocation_deletion_and_isolation(self):
  self.assertEqual(sources(self.ws,self.b)['items'],[])
  with self.assertRaises(LookupError):save(self.ws,self.b,{'version':0,'config':{'title':'Outro','widgets':[self.widget()]}})
  self.ws.share(self.a,self.table['id'],'b@example.org','read')
  save(self.ws,self.b,{'version':0,'config':{'title':'Outro','widgets':[self.widget()]}})
  self.assertEqual(get(self.ws,self.b)['results'][0]['value'],28)
  self.ws.share(self.a,self.table['id'],'b@example.org','remove')
  result=get(self.ws,self.b)['results'][0];self.assertIn('error',result);self.assertNotIn('value',result);self.assertNotIn('sourceTitle',result)
  self.save([self.widget()]);self.ws.update(self.a,self.table['id'],dict(self.table,deleted=True))
  self.assertIn('error',get(self.ws,self.a)['results'][0]);self.assertEqual(get(self.ws,self.b)['config']['title'],'Outro')
 def test_conflict_validation_and_column_identity(self):
  self.save([self.widget()])
  with self.assertRaises(Conflict):self.save([],0)
  with self.assertRaises(InvalidInput):self.save([self.widget(),self.widget()],1)
  with self.assertRaises(InvalidInput):self.save([self.widget(groupField={'index':True,'name':'Valor'})],1)
  self.ws.update(self.a,self.table['id'],dict(self.table,content={'columns':['Equipe','Renomeado'],'rows':[['A','1']]}))
  self.assertIn('error',get(self.ws,self.a)['results'][0])
  self.save([],1);self.assertEqual(get(self.ws,self.a)['results'],[])
 def test_no_silent_numeric_or_category_truncation(self):
  self.save([self.widget()]);current=self.ws.update(self.a,self.table['id'],dict(self.table,content={'columns':['Equipe','Valor'],'rows':[['A','1,50']]}))
  self.assertIn('error',get(self.ws,self.a)['results'][0])
  current=self.ws.update(self.a,self.table['id'],dict(current,content={'columns':['Equipe','Valor'],'rows':[['A','']]}))
  self.assertIsNone(get(self.ws,self.a)['results'][0]['value'])
  current=self.ws.update(self.a,self.table['id'],dict(current,content={'columns':['Equipe','Valor'],'rows':[[str(i),'1'] for i in range(51)]}))
  self.save([self.widget(groupField={'index':0,'name':'Equipe'})],1)
  self.assertIn('50 categorias',get(self.ws,self.a)['results'][0]['error'])
 def test_project_categories_and_no_empty_averages(self):
  board=self.ws.create(self.a,{'kind':'board','title':'Projeto','content':{'tasks':[{'id':'t1','title':'Fazer','status':'A fazer','priority':'Alta','due':''},{'id':'t2','title':'Feito','status':'Concluído','priority':'Normal','due':''}]}})
  self.save([self.widget(sourceId=board['id'],operation='count',valueField=None,groupField={'index':1,'name':'Estado'})])
  self.assertEqual(get(self.ws,self.a)['results'][0]['groups'],[{'label':'A fazer','value':1},{'label':'Concluído','value':1}])
if __name__=='__main__':unittest.main()
