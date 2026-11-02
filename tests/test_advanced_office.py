import base64,copy,io,tempfile,unittest
from pathlib import Path
from openpyxl import load_workbook
from pptx import Presentation
from docx import Document
from server.store import Store,InvalidInput
from server.workspace import Workspace
from server.schema import validate_content
from server.office import export_file,import_file
from tests import test_spreadsheet
from tests.test_slides import content

class AdvancedOfficeTest(unittest.TestCase):
    def test_sheet_protection_enforced_for_shared_editor(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'test.sqlite');ws=Workspace(store)
            owner=store.register('owner@example.org','Owner','Test-password-123')['id'];editor=store.register('editor@example.org','Editor','Test-password-123')['id']
            c=test_spreadsheet.SpreadsheetTest().fixture()['content'];c['protectedRanges']=[{'sheetId':'sheet-0','range':'B2','name':'Valor'}]
            item=ws.create(owner,{'kind':'sheet','title':'Protegida','content':c});ws.share(owner,item['id'],'editor@example.org','edit')
            def update(who,mutate):
                new=copy.deepcopy(item['content']);mutate(new);return ws.update(who,item['id'],{'title':item['title'],'content':new,'version':item['version']})
            with self.assertRaises(PermissionError):update(editor,lambda n:n['workbook']['sheets']['sheet-0']['cellData']['1']['1'].update(v=999))
            with self.assertRaises(PermissionError):update(editor,lambda n:n.update(protectedRanges=[]))
            with self.assertRaises(PermissionError):update(editor,lambda n:n.update(links=[{'sheetId':'sheet-0','cell':'B2','type':'url','url':'https://example.org'}]))
            item=update(editor,lambda n:n['workbook']['sheets']['sheet-0']['cellData']['0']['0'].update(v='Permitido'))
            item=update(owner,lambda n:n['workbook']['sheets']['sheet-0']['cellData']['1']['1'].update(v=999))
            self.assertEqual(ws.get(editor,item['id'])['content']['workbook']['sheets']['sheet-0']['cellData']['1']['1']['v'],999)
    def test_all_new_charts_export_native_excel(self):
        for kind,expected in [('area','AreaChart'),('doughnut','DoughnutChart'),('horizontal','BarChart'),('scatter','ScatterChart'),('radar','RadarChart')]:
            item=test_spreadsheet.SpreadsheetTest().fixture();item['content']['charts']=[{'id':'c','type':kind,'title':'Dados','sheetId':'sheet-0','range':'A1:B2'}]
            validate_content('sheet',item['content']);data,_=export_file(item,'xlsx');chart=load_workbook(io.BytesIO(data)).worksheets[0]._charts[0]
            self.assertEqual(type(chart).__name__,expected)
    def test_groups_rotation_roundtrip(self):
        c=content();objects=c['slides'][0]['objects'];objects[1]['group']='group-1';objects[2]['group']='group-1';objects[1]['rotation']=25
        data,_=export_file({'kind':'slides','title':'Grupos','content':c},'pptx');deck=Presentation(io.BytesIO(data));self.assertTrue(any(s.shape_type==6 for s in deck.slides[0].shapes))
        result,_=import_file('Grupos.pptx',base64.b64encode(data).decode());validate_content('slides',result['content']);actual=result['content']['slides'][0]['objects'];text=next(o for o in actual if o.get('text')=='Meta 2027');shape=next(o for o in actual if o.get('text')=='OK')
        self.assertEqual(text['group'],shape['group']);self.assertAlmostEqual(text['rotation'],25);self.assertAlmostEqual(text['x'],objects[1]['x'],places=3)
    def test_tabs_export_all_content_and_reject_inconsistent_active_tab(self):
        c={'text':'Segundo','tabs':[{'id':'a','name':'Primeira','text':'Primeiro'},{'id':'b','name':'Segunda','text':'Segundo'}],'activeTab':1}
        validate_content('document',c);data,_=export_file({'kind':'document','title':'Abas','content':c},'docx');text='\n'.join(p.text for p in Document(io.BytesIO(data)).paragraphs)
        for value in ['Primeira','Primeiro','Segunda','Segundo']:self.assertIn(value,text)
        c['text']='inconsistente'
        with self.assertRaises(InvalidInput):validate_content('document',c)
