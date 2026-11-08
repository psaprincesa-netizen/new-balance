import tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from server.store import Store,InvalidInput
from server.workspace import Workspace,Conflict
from server.automations import configure,settings,retry
from server.forms import form_schema
class AutomationTest(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.store=Store(Path(tmp.name)/'automation.sqlite');self.ws=Workspace(self.store)
        self.a=self.store.register('a@example.org','Ana','long-test-password')['id'];self.b=self.store.register('b@example.org','Bia','long-test-password')['id']
        self.board=self.ws.create(self.a,{'kind':'board','title':'Projeto','content':{'tasks':[]}})
        self.form=self.ws.create(self.a,{'kind':'form','title':'Pedidos','content':{'questions':['Criar?','Título'],'fields':[{'type':'choice','options':['Sim','Não'],'required':True},{'type':'text','options':[],'required':True}],'responses':[]}})
        self.token=self.ws.publication(self.a,self.form['id'],True)['token'];self.schema=form_schema(self.form['content'])['schema_id']
        self.config={'enabled':True,'version':1,'targetId':self.board['id'],'titleQuestion':1,'whenQuestion':0,'whenValue':'Sim','prefix':'Pedido: ','priority':'Alta'}
        configure(self.ws,self.a,self.form['id'],self.config)
    def send(self,answers=None,key='synthetic-request-001'):
        return self.ws.submit_form(self.token,answers or ['Sim','Entrega'],self.schema,key)
    def enable_approval(self):
        configure(self.ws,self.a,self.form['id'],dict(self.config,requireApproval=True))
    def test_approval_waits_and_concurrent_decisions_do_not_duplicate_tasks(self):
        from server.automations import decide
        self.enable_approval();self.send()
        run=settings(self.ws,self.a,self.form['id'])['runs'][0]
        self.assertEqual(run['status'],'awaiting_approval');self.assertFalse(self.ws.get(self.a,self.board['id'])['content']['tasks'])
        with self.assertRaises(InvalidInput):retry(self.ws,self.a,self.form['id'],run['id'])
        with ThreadPoolExecutor(max_workers=4) as executor:list(executor.map(lambda _:decide(self.ws,self.a,self.form['id'],run['id'],'approve'),range(4)))
        run=settings(self.ws,self.a,self.form['id'])['runs'][0]
        self.assertEqual(run['status'],'completed');self.assertEqual(run['approval']['actor'],self.a)
        self.assertEqual(run['approval']['decision'],'approve');self.assertGreater(run['approval']['at'],0)
        self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)
        with self.assertRaises(Conflict):decide(self.ws,self.a,self.form['id'],run['id'],'reject')
    def test_rejection_is_final_and_shared_editor_cannot_decide(self):
        from server.automations import decide
        self.enable_approval();self.send();run=settings(self.ws,self.a,self.form['id'])['runs'][0]
        self.ws.share(self.a,self.form['id'],'b@example.org','edit')
        with self.assertRaises(PermissionError):decide(self.ws,self.b,self.form['id'],run['id'],'approve')
        decide(self.ws,self.a,self.form['id'],run['id'],'reject');decide(self.ws,self.a,self.form['id'],run['id'],'reject')
        self.assertFalse(self.ws.get(self.a,self.board['id'])['content']['tasks'])
        self.assertEqual(settings(self.ws,self.a,self.form['id'])['runs'][0]['status'],'rejected')
        with self.assertRaises(Conflict):decide(self.ws,self.a,self.form['id'],run['id'],'approve')
        with self.assertRaises(InvalidInput):retry(self.ws,self.a,self.form['id'],run['id'])
    def test_original_response_snapshot_is_private_and_survives_source_edits(self):
        from server.automations import review
        self.enable_approval();self.send();run=settings(self.ws,self.a,self.form['id'])['runs'][0]
        self.assertNotIn('review',run)
        snapshot=review(self.ws,self.a,self.form['id'],run['id']);self.assertEqual(snapshot['answers'],['Sim','Entrega'])
        current=self.ws.get(self.a,self.form['id']);current['content']['responses']=[];self.ws.update(self.a,self.form['id'],current)
        self.assertEqual(review(self.ws,self.a,self.form['id'],run['id']),snapshot)
        self.ws.share(self.a,self.form['id'],'b@example.org','edit')
        with self.assertRaises(PermissionError):review(self.ws,self.b,self.form['id'],run['id'])

    def test_approval_failure_can_retry_after_destination_restored(self):
        from server.automations import decide
        self.enable_approval();self.send();run=settings(self.ws,self.a,self.form['id'])['runs'][0]
        deleted=self.ws.update(self.a,self.board['id'],dict(self.board,deleted=True))
        decide(self.ws,self.a,self.form['id'],run['id'],'approve')
        failed=settings(self.ws,self.a,self.form['id'])['runs'][0];self.assertEqual(failed['status'],'failed');self.assertEqual(failed['approval']['decision'],'approve')
        self.ws.update(self.a,self.board['id'],dict(deleted,deleted=False));retry(self.ws,self.a,self.form['id'],run['id'])
        self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)
    def test_interrupted_approval_rolls_back_decision_and_effect_together(self):
        from server.automations import decide,execute_run
        self.enable_approval();self.send();run=settings(self.ws,self.a,self.form['id'])['runs'][0]
        def crash(*args):execute_run(*args);raise RuntimeError('interrupted approval')
        with patch('server.automations.execute_run',side_effect=crash):
            with self.assertRaises(RuntimeError):decide(self.ws,self.a,self.form['id'],run['id'],'approve')
        current=settings(self.ws,self.a,self.form['id'])['runs'][0]
        self.assertEqual(current['status'],'awaiting_approval');self.assertIsNone(current['approval']['decision'])
        self.assertFalse(self.ws.get(self.a,self.board['id'])['content']['tasks'])
        decide(self.ws,self.a,self.form['id'],run['id'],'approve')
        self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)
    def test_disabled_rule_keeps_pending_approval_and_skips_unmatched_conditions(self):
        from server.automations import decide
        self.enable_approval();self.send(['Não','Ignorada']);self.send(key='synthetic-request-002')
        runs=settings(self.ws,self.a,self.form['id'])['runs'];self.assertEqual(sorted(r['status'] for r in runs),['awaiting_approval','skipped'])
        pending=next(r for r in runs if r['status']=='awaiting_approval')
        current=self.ws.get(self.a,self.form['id']);configure(self.ws,self.a,self.form['id'],{'enabled':False,'version':current['version']})
        decide(self.ws,self.a,self.form['id'],pending['id'],'approve')
        self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)

    def test_rule_and_response_retries_are_atomic_and_idempotent(self):
        first=self.send();self.assertEqual(self.send(),first)
        source=self.ws.get(self.a,self.form['id']);target=self.ws.get(self.a,self.board['id'])
        self.assertEqual(len(source['content']['responses']),1);self.assertEqual(source['version'],2)
        self.assertEqual(target['version'],2);self.assertEqual(len(target['content']['tasks']),1)
        self.assertEqual(target['content']['tasks'][0]['title'],'Pedido: Entrega')
        self.assertEqual(target['content']['tasks'][0]['priority'],'Alta')
        run=settings(self.ws,self.a,self.form['id'])['runs'][0]
        self.assertEqual(run['status'],'completed')
        retry(self.ws,self.a,self.form['id'],run['id'])
        self.assertEqual(self.ws.get(self.a,self.board['id'])['version'],2)
        with self.assertRaises(Conflict):self.send(['Sim','Outra entrega'])
    def test_failure_after_task_write_rolls_back_response_task_run_and_idempotency_record(self):
        from server.automations import execute_run
        def crash_after_write(*args):
            execute_run(*args)
            raise RuntimeError('synthetic interruption')
        with patch('server.automations.execute_run',side_effect=crash_after_write):
            with self.assertRaises(RuntimeError):self.send()
        self.assertEqual(self.ws.get(self.a,self.form['id'])['content']['responses'],[])
        self.assertEqual(self.ws.get(self.a,self.board['id'])['content']['tasks'],[])
        self.assertEqual(settings(self.ws,self.a,self.form['id'])['runs'],[])
        self.send()
        self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)

    def test_concurrent_duplicate_requests_create_one_effect(self):
        with ThreadPoolExecutor(max_workers=4) as executor:list(executor.map(lambda _:self.send(),range(4)))
        self.assertEqual(len(self.ws.get(self.a,self.form['id'])['content']['responses']),1)
        self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)
        self.assertEqual(len(settings(self.ws,self.a,self.form['id'])['runs']),1)
    def test_condition_disabled_and_failed_destination_are_visible_to_owner(self):
        self.send(['Não','Sem tarefa'])
        self.assertEqual(settings(self.ws,self.a,self.form['id'])['runs'][0]['status'],'skipped')
        self.assertFalse(self.ws.get(self.a,self.board['id'])['content']['tasks'])
        target=self.ws.update(self.a,self.board['id'],dict(self.board,deleted=True))
        self.send(key='synthetic-request-002')
        run=settings(self.ws,self.a,self.form['id'])['runs'][0];self.assertEqual(run['status'],'failed')
        target=self.ws.update(self.a,self.board['id'],dict(target,deleted=False))
        retry(self.ws,self.a,self.form['id'],run['id']);retry(self.ws,self.a,self.form['id'],run['id'])
        self.assertEqual(len(self.ws.get(self.a,self.board['id'])['content']['tasks']),1)
        current=self.ws.get(self.a,self.form['id'])
        configure(self.ws,self.a,self.form['id'],{'enabled':False,'version':current['version']})
        self.send(key='synthetic-request-003')
        self.assertEqual(len(settings(self.ws,self.a,self.form['id'])['runs']),2)
    def test_other_users_cannot_configure_view_or_retry_and_shared_boards_are_not_destinations(self):
        self.ws.share(self.a,self.form['id'],'b@example.org','edit')
        for action in [lambda:settings(self.ws,self.b,self.form['id']),lambda:configure(self.ws,self.b,self.form['id'],self.config),lambda:retry(self.ws,self.b,self.form['id'],'unknown')]:
            with self.assertRaises(PermissionError):action()
        foreign=self.ws.create(self.b,{'kind':'board','title':'Outro','content':{'tasks':[]}})
        self.ws.share(self.b,foreign['id'],'a@example.org','edit')
        with self.assertRaises(InvalidInput):configure(self.ws,self.a,self.form['id'],dict(self.config,targetId=foreign['id']))
        with self.assertRaises(Conflict):configure(self.ws,self.a,self.form['id'],dict(self.config,version=2))
    def test_question_changes_fail_safely_without_reprocessing_the_wrong_answer(self):
        changed=dict(self.form,content=dict(self.form['content'],questions=['Criar?','Novo título']))
        changed=self.ws.update(self.a,self.form['id'],changed)
        schema=form_schema(changed['content'])['schema_id']
        self.ws.submit_form(self.token,['Sim','Entrega'],schema,'synthetic-new-request')
        run=settings(self.ws,self.a,self.form['id'])['runs'][0]
        self.assertEqual(run['status'],'failed');self.assertFalse(run['retryable'])
        with self.assertRaises(InvalidInput):retry(self.ws,self.a,self.form['id'],run['id'])
        self.assertFalse(self.ws.get(self.a,self.board['id'])['content']['tasks'])
