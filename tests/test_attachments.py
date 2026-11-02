import base64,io,tempfile,unittest
from pathlib import Path
from docx import Document
from server.attachments import valid_attachments
from server.schema import validate_content
from server.store import Store,InvalidInput
from server.workspace import Workspace
from tests import test_api

class AttachmentTest(unittest.TestCase):
    def test_binary_and_metadata_validation(self):
        data=b'%PDF\x00\xff\x01';entry={'id':'one','kind':'file','name':'Arquivo.pdf','size':len(data),'data':base64.b64encode(data).decode()}
        self.assertTrue(valid_attachments([entry]))
        for key,value in [('size',1),('size',True),('data','!!!!'),('name','../file'),('name','bad\nfile'),('kind','script')]:
            bad={**entry,key:value};self.assertFalse(valid_attachments([bad]),(key,value))
        self.assertFalse(valid_attachments([entry,entry]));self.assertFalse(valid_attachments([entry]*21))
        self.assertFalse(valid_attachments([{'id':'big','kind':'file','name':'big','size':1000001,'data':base64.b64encode(b'x'*1000001).decode()}]))
        for url in ['javascript:alert(1)','data:text/html,hello','https://a:b@example.org','https://example.org\n/x']:
            self.assertFalse(valid_attachments([{'id':'link','kind':'link','name':'Site','url':url}]))
        self.assertTrue(valid_attachments([{'id':'link','kind':'link','name':'Site','url':'https://example.org/path?q=1'}]))
        self.assertTrue(valid_attachments([{'id':'ref','kind':'item','name':'Privado','itemId':'a'*32}]))
        for kind,content in [('document',{'text':'Hello'}),('slides',{'slides':[{'title':'A','body':'','notes':''}]}),('sheet',{'cells':[['1']]})]:
            validate_content(kind,{**content,'attachments':[entry]})
            with self.assertRaises(InvalidInput):validate_content(kind,{**content,'attachments':[{'kind':'bad'}]})
    def test_persistence_history_and_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'db.sqlite');work=Workspace(store)
            owner=store.register('owner@example.org','Owner','long-password-test-123')['id'];reader=store.register('reader@example.org','Reader','long-password-test-123')['id']
            entry={'id':'one','kind':'file','name':'data.bin','size':3,'data':'AAH/'}
            item=work.create(owner,{'kind':'document','title':'Anexo','content':{'text':'Original','attachments':[entry]}})
            with self.assertRaises(LookupError):work.get(reader,item['id'])
            work.share(owner,item['id'],'reader@example.org','read');self.assertEqual(work.get(reader,item['id'])['content']['attachments'][0],entry)
            with self.assertRaises(PermissionError):work.update(reader,item['id'],item)
            item['content']['attachments']=[];work.update(owner,item['id'],item)
            self.assertEqual(work.history(owner,item['id'])[-1]['content']['attachments'],[entry])
            work.share(owner,item['id'],'reader@example.org','remove')
            with self.assertRaises(LookupError):work.get(reader,item['id'])

class InsertionApiTest(unittest.TestCase):
    setUp = test_api.ApiTest.setUp
    tearDown = test_api.ApiTest.tearDown
    request = test_api.ApiTest.request
    def test_docx_preview_requires_auth_and_does_not_create_a_file(self):
        document=Document();document.add_paragraph('Conteúdo inserido');output=io.BytesIO();document.save(output)
        payload={'name':'Conteúdo.docx','data':base64.b64encode(output.getvalue()).decode()}
        self.assertEqual(self.request('POST','/api/import/preview',payload)[0],401)
        account={'name':'Editor','email':'editor@example.org','password':'long-test-password-123'};self.request('POST','/api/register',account)
        headers={'Content-Type':'application/json','Cookie':self.request('POST','/api/login',account)[2].split(';')[0]}
        status,result,_=self.request('POST','/api/import/preview',payload,headers)
        self.assertEqual(status,200);self.assertIn('Conteúdo inserido',result['content']['text']);self.assertTrue(result['warnings'])
        self.assertEqual(self.request('GET','/api/items',headers=headers)[1]['items'],[])
        self.assertEqual(self.request('POST','/api/import/preview',{**payload,'name':'wrong.xlsx'},headers)[0],400)
        self.assertEqual(self.request('POST','/api/import/preview',{**payload,'data':'invalid'},headers)[0],400)
