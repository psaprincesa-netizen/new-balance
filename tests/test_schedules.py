import tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from server.store import Store,InvalidInput
from server.workspace import Workspace,Conflict
from server.schedules import save,listing,history,process_rule,process_due,retry,trash,next_day

class SchedulesTest(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.store=Store(Path(tmp.name)/'schedules.sqlite');self.ws=Workspace(self.store)
  self.a=self.store.register('a@example.org','Ana','long-test-password')['id'];self.b=self.store.register('b@example.org','Bia','long-test-password')['id']
  self.board=self.ws.create(self.a,{'kind':'board','title':'Projeto','content':{'tasks':[]}})
  self.now=datetime(2026,1,31,12,tzinfo=timezone.utc)
  self.config={'name':'Rotina','targetId':self.board['id'],'taskTitle':'Revisão mensal','priority':'Alta','cadence':'monthly','firstDate':'2026-01-31','timezone':'UTC','dueOffset':2}
 def create(self,**changes):return save(self.ws,self.a,{'version':0,'active':True,'config':dict(self.config,**changes)},now=self.now)['id']
 def test_month_end_anchor_and_concurrent_idempotency(self):
  ident=self.create()
  with ThreadPoolExecutor(max_workers=4) as executor:list(executor.map(lambda _:process_rule(self.ws,ident,self.a,self.now),range(4)))
  self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)
  self.assertEqual(listing(self.ws,self.a)['items'][0]['next_due'],'2026-02-28')
  later=datetime(2026,2,28,12,tzinfo=timezone.utc);process_rule(self.ws,ident,self.a,later)
  self.assertEqual(listing(self.ws,self.a)['items'][0]['next_due'],'2026-03-31')
  self.assertEqual(self.ws.get(self.a,self.board['id'])['content']['tasks'][0]['due'],'2026-02-02')
  self.assertEqual(len(history(self.ws,self.a,ident)['items']),2)
 def test_failure_snapshot_retry_disable_and_restore(self):
  ident=self.create(cadence='once');deleted=self.ws.update(self.a,self.board['id'],dict(self.board,deleted=True))
  process_rule(self.ws,ident,self.a,self.now);run=history(self.ws,self.a,ident)['items'][0]
  self.assertEqual(run['status'],'failed');self.assertFalse(listing(self.ws,self.a)['items'][0]['active'])
  self.ws.update(self.a,self.board['id'],dict(deleted,deleted=False));retry(self.ws,self.a,ident,run['id']);retry(self.ws,self.a,ident,run['id'])
  self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)
  row=listing(self.ws,self.a)['items'][0];trash(self.ws,self.a,ident,True,row['version'])
  self.assertEqual(listing(self.ws,self.a)['items'],[])
  with self.assertRaises(InvalidInput):retry(self.ws,self.a,ident,run['id'])
  row=listing(self.ws,self.a,True)['items'][0];trash(self.ws,self.a,ident,False,row['version']);self.assertFalse(listing(self.ws,self.a)['items'][0]['active'])
 def test_timezones_future_dates_bounded_catchup_and_restart(self):
  ident=self.create(cadence='daily',timezone='America/Los_Angeles')
  early=datetime(2026,1,31,2,tzinfo=timezone.utc)
  self.assertEqual(process_rule(self.ws,ident,self.a,early)['processed'],0)
  later=datetime(2026,2,10,12,tzinfo=timezone.utc)
  self.assertEqual(process_rule(self.ws,ident,self.a,later)['processed'],5)
  self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),5)
  process_due(Workspace(self.store),self.a,later)
  self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),10)
 def test_owner_only_destinations_and_optimistic_edits(self):
  ident=self.create();self.assertEqual(listing(self.ws,self.b)['items'],[])
  for task in [lambda:history(self.ws,self.b,ident),lambda:process_rule(self.ws,ident,self.b,self.now),lambda:trash(self.ws,self.b,ident,True,1)]:
   with self.assertRaises(LookupError):task()
  other=self.ws.create(self.b,{'kind':'board','title':'Outro','content':{'tasks':[]}});self.ws.share(self.b,other['id'],'a@example.org','edit')
  with self.assertRaises(InvalidInput):self.create(targetId=other['id'])
  process_rule(self.ws,ident,self.a,self.now)
  with self.assertRaises(Conflict):save(self.ws,self.a,{'version':1,'active':True,'config':self.config},ident,self.now)
 def test_interrupted_effect_rolls_back_run_task_and_next_date(self):
  from server.schedules import effect
  ident=self.create()
  def crash(*args):effect(*args);raise RuntimeError('interruption')
  with patch('server.schedules.effect',side_effect=crash):
   with self.assertRaises(RuntimeError):process_rule(self.ws,ident,self.a,self.now)
  self.assertEqual(history(self.ws,self.a,ident)['items'],[]);self.assertFalse(self.ws.get(self.a,self.board['id'])['content']['tasks'])
  self.assertEqual(listing(self.ws,self.a)['items'][0]['next_due'],'2026-01-31')
  process_rule(self.ws,ident,self.a,self.now);self.assertEqual(len(history(self.ws,self.a,ident)['items']),1)
 def test_configuration_changes_preserve_existing_occurrence_snapshot(self):
  ident=self.create();process_rule(self.ws,ident,self.a,self.now);row=listing(self.ws,self.a)['items'][0]
  new=dict(self.config,taskTitle='Novo título');save(self.ws,self.a,{'version':row['version'],'active':True,'config':new},ident,self.now)
  self.assertEqual(listing(self.ws,self.a)['items'][0]['next_due'],'2026-02-28')
  self.assertEqual(history(self.ws,self.a,ident)['items'][0]['title'],'Revisão mensal')
  with self.assertRaises(InvalidInput):self.create(timezone='invalid/zone')
  with self.assertRaises(InvalidInput):self.create(firstDate='2026-01-30')
 def test_daily_batch_supports_fifty_rules_without_duplicate_effects(self):
  for i in range(50):self.create(name='Rotina '+str(i),cadence='once')
  self.assertEqual(process_due(self.ws,now=self.now,limit=200)['processed'],50)
  self.assertEqual(process_due(self.ws,now=self.now,limit=200)['processed'],0)
  self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),50)
 def test_cron_authentication_fails_closed_and_uses_native_daily_config(self):
  import os,json,threading,http.client
  from http.server import ThreadingHTTPServer
  from server.app import handler_for
  server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.store));threading.Thread(target=server.serve_forever,daemon=True).start()
  self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  def request(header=None,probe=False):
   conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
   conn.request('GET','/api/index?route=cron/schedules'+('&probe=1' if probe else ''),headers={'Authorization':header} if header else {})
   response=conn.getresponse();response.read();status=response.status;conn.close();return status
  with patch.dict(os.environ,{'CRON_SECRET':'synthetic-cron-test-secret'}),patch('server.schedules.process_due',return_value={'processed':0}) as runner:
   self.assertEqual(request(),401);self.assertEqual(request('Bearer wrong'),401);runner.assert_not_called()
   self.assertEqual(request('Bearer synthetic-cron-test-secret',True),200);runner.assert_not_called()
   self.assertEqual(request('Bearer synthetic-cron-test-secret'),200);self.assertEqual(runner.call_count,1)
  with patch.dict(os.environ,{'CRON_SECRET':''}):self.assertEqual(request('Bearer synthetic-cron-test-secret'),401)
  config=json.loads(Path('vercel.json').read_text());self.assertEqual(config['crons'],[{'path':'/api/cron/schedules','schedule':'0 3 * * *'}])
if __name__=='__main__':unittest.main()
