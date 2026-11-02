import base64,hashlib,json,os,tempfile,time,unittest
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from unittest.mock import patch
from cryptography.fernet import Fernet
from server.store import Store,InvalidInput
from server.workspace import Workspace
from server.google_workspace import GoogleWorkspace,SCOPES

class GoogleWorkspaceTest(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.store=Store(Path(temp.name)/'test.sqlite');Workspace(self.store)
        self.user=self.store.register('google@example.org','Google','Test-password-123')['id']
        self.other=self.store.register('other@example.org','Other','Test-password-123')['id']
        self.google=GoogleWorkspace(self.store)
        env=patch.dict(os.environ,{'GOOGLE_CLIENT_ID':'test-client','GOOGLE_CLIENT_SECRET':'test-secret','GOOGLE_TOKEN_ENCRYPTION_KEY':Fernet.generate_key().decode()});env.start();self.addCleanup(env.stop)
    def begin(self):return {key:value[0] for key,value in parse_qs(urlparse(self.google.start(self.user)['url']).query).items()}
    def saved(self):self.google.save(self.user,{'access_token':'access-test','refresh_token':'refresh-test','expires_at':time.time()+3600,'email':'google@example.org'})
    def test_pkce_user_binding_one_use_and_encryption(self):
        query=self.begin();state=query['state']
        with self.assertRaises(InvalidInput):self.google.callback(self.other,{'state':state,'code':'test-code'})
        with self.store.connect() as db:row=db.execute('SELECT * FROM google_oauth_states').fetchone()
        self.assertNotEqual(row['digest'],state)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(row['verifier'].encode()).digest()).decode().rstrip('=');self.assertEqual(query['code_challenge'],challenge)
        with patch('server.google_workspace.request_json',side_effect=[{'access_token':'access-test','refresh_token':'refresh-test','scope':SCOPES},{'email':'google@example.org'}]) as request:
            self.google.callback(self.user,{'state':state,'code':'test-code'})
            self.assertEqual(request.call_args_list[0].args[1]['code_verifier'],row['verifier'])
        with self.assertRaises(InvalidInput):self.google.callback(self.user,{'state':state,'code':'test-code'})
        with self.store.connect() as db:encrypted=db.execute('SELECT encrypted FROM google_connections').fetchone()['encrypted']
        self.assertNotIn('refresh-test',encrypted);self.assertNotIn('access-test',encrypted)
        self.assertEqual(self.google.status(self.user),{'configured':True,'connected':True,'email':'google@example.org'})
        self.assertFalse(self.google.status(self.other)['connected'])
    def test_expiration_and_partial_consent(self):
        query=self.begin()
        with self.store.connect() as db:db.execute('UPDATE google_oauth_states SET expires=0')
        with self.assertRaises(InvalidInput):self.google.callback(self.user,{'state':query['state'],'code':'code'})
        query=self.begin()
        with patch('server.google_workspace.request_json',return_value={'access_token':'access','refresh_token':'refresh','scope':'openid email'}),self.assertRaises(InvalidInput):self.google.callback(self.user,{'state':query['state'],'code':'code'})
        self.assertFalse(self.google.status(self.user)['connected'])
    def test_refresh_send_and_meet_use_real_api_contracts(self):
        self.google.save(self.user,{'access_token':'old','refresh_token':'refresh-test','expires_at':0})
        with patch('server.google_workspace.request_json',return_value={'access_token':'renewed','expires_in':3600}) as request:self.assertEqual(self.google.token(self.user),'renewed')
        self.assertEqual(request.call_args.args[1]['grant_type'],'refresh_token')
        with patch('server.google_workspace.request_json',return_value={'id':'message-id'}) as request:
            self.google.post(self.user,'send',{'to':'recipient@example.org','subject':'Teste','body':'Olá'})
            raw=base64.urlsafe_b64decode(request.call_args.args[1]['raw']);self.assertIn(b'To: recipient@example.org',raw)
            with self.assertRaises(InvalidInput):self.google.post(self.user,'send',{'to':'recipient@example.org','subject':'Bad\r\nBcc: other@example.org','body':'x'})
        with patch('server.google_workspace.request_json',return_value={'id':'event-id'}) as request:
            self.google.post(self.user,'event',{'title':'Reunião','start':'2026-11-01T10:00:00Z','end':'2026-11-01T11:00:00Z','meet':True})
            payload=request.call_args.args[1];self.assertIn('conferenceData',payload);self.assertNotIn('attendees',payload)
            with self.assertRaises(InvalidInput):self.google.post(self.user,'event',{'title':'Bad','start':'2026-11-01T10:00:00','end':'2026-11-01T11:00:00'})
        with patch('server.google_workspace.request_json',return_value={}):self.google.disconnect(self.user)
        self.assertFalse(self.google.status(self.user)['connected'])
