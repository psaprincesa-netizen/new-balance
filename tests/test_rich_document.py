import io,unittest,zipfile
from docx import Document
from server.rich_document import valid_rich
from server.document_io import export_document,import_document
from server.schema import validate_content
from server.store import InvalidInput
class RichDocumentTest(unittest.TestCase):
    def fixture(self):
        return {'text':'Título\nTexto formatado','page':{'header':'Empresa','footer':'Confidencial','pageNumbers':True},'rich':{'type':'doc','content':[{'type':'heading','attrs':{'level':2},'content':[{'type':'text','text':'Título'}]},{'type':'tableOfContents'},{'type':'paragraph','attrs':{'textAlign':'center','lineHeight':2,'indent':1},'content':[{'type':'text','text':'Texto formatado','marks':[{'type':'underline'},{'type':'strike'},{'type':'textStyle','attrs':{'fontFamily':'Georgia','fontSize':24,'color':'#123456','backgroundColor':'#ffff00'}}]},{'type':'footnote','attrs':{'id':'nota-1','text':'Referência bibliográfica'}}]},{'type':'pageBreak'},{'type':'paragraph','content':[{'type':'text','text':'Fim'}]}]}}
    def test_rich_roundtrip_and_real_docx_properties(self):
        c=self.fixture();validate_content('document',c);out=io.BytesIO();export_document(c,'Teste',out);out.seek(0);doc=Document(out)
        p=next(p for p in doc.paragraphs if 'Texto formatado' in p.text);r=p.runs[0]
        self.assertTrue(r.underline);self.assertTrue(r.font.strike);self.assertEqual(r.font.name,'Georgia');self.assertEqual(r.font.size.pt,24);self.assertEqual(str(r.font.color.rgb),'123456');self.assertEqual(doc.sections[0].header.paragraphs[0].text,'Empresa')
        out.seek(0)
        with zipfile.ZipFile(out) as z:self.assertIn(b'Refer',z.read('word/footnotes.xml'));self.assertIn(b'PAGE',z.read('word/footer1.xml'))
        out.seek(0);restored=import_document(out);self.assertTrue(valid_rich(restored['rich']));self.assertIn('textStyle',str(restored['rich']));self.assertIn('footnote',str(restored['rich']));self.assertTrue(restored['page']['pageNumbers'])
    def test_unsafe_rich_attributes_are_rejected(self):
        for attrs in [{'color':'red; background:url(https://bad.test)'},{'fontFamily':'bad'},{'fontSize':999},{'href':'javascript:alert(1)'},{'onerror':'x'}]:
            c=self.fixture();c['rich']['content']=[{'type':'paragraph','content':[{'type':'text','text':'x','marks':[{'type':'textStyle','attrs':attrs}]}]}]
            with self.assertRaises(InvalidInput):validate_content('document',c)
    def test_vertical_merge_roundtrip_and_bounded_table(self):
        doc=Document();table=doc.add_table(rows=2,cols=2);table.cell(0,0).merge(table.cell(1,0)).text='Mesclada';table.cell(0,1).text='A';table.cell(1,1).text='B';data=io.BytesIO();doc.save(data);data.seek(0)
        c=import_document(data);validate_content('document',c);table_node=next(n for n in c['rich']['content'] if n['type']=='table');self.assertEqual(table_node['content'][0]['content'][0]['attrs']['rowspan'],2)
        out=io.BytesIO();export_document(c,'Tabela',out);out.seek(0);again=Document(out);self.assertEqual(again.tables[0].cell(1,0).text,'Mesclada')
        table_node['content'][0]['content'][0]['attrs']['colspan']=1000
        with self.assertRaises(InvalidInput):validate_content('document',c)
