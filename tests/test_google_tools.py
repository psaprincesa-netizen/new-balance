import base64,io,unittest
from docx import Document
from pptx import Presentation
from server.office import export_file,import_file
from server.schema import validate_content
from server.store import InvalidInput

class GoogleToolsTest(unittest.TestCase):
    def test_page_configuration_export_and_import(self):
        content={'text':'# Relatório\nTexto','page':{'size':'A4','orientation':'landscape','margin':15,'font':'Georgia','fontSize':14,'lineHeight':2,'align':'justify','mode':'wide'}}
        validate_content('document',content)
        data,_=export_file({'kind':'document','title':'Relatório','content':content},'docx')
        doc=Document(io.BytesIO(data));section=doc.sections[0]
        self.assertAlmostEqual(section.page_width.mm,297,places=1)
        self.assertAlmostEqual(section.left_margin.mm,15,places=1)
        self.assertEqual(doc.styles['Normal'].font.name,'Georgia')
        self.assertEqual(doc.styles['Normal'].font.size.pt,14)
        restored,_=import_file('Relatório.docx',base64.b64encode(data).decode())
        self.assertEqual(restored['content']['page']['orientation'],'landscape')
        self.assertEqual(restored['content']['page']['font'],'Georgia')
    def test_document_with_implicit_page_dimensions(self):
        doc=Document();doc.add_paragraph('Preservar texto');section=doc.sections[0]
        for tag in ['w:pgSz','w:pgMar']:
            for node in section._sectPr.xpath('./'+tag):section._sectPr.remove(node)
        output=io.BytesIO();doc.save(output)
        restored,_=import_file('Texto.docx',base64.b64encode(output.getvalue()).decode())
        self.assertIn('Preservar texto',restored['content']['text'])
        validate_content('document',restored['content'])

    def test_slide_configuration_roundtrip(self):
        for transition in ['fade','push']:
            slide={'title':'Plano','body':'Texto','notes':'Privado','hidden':True,'background':'#123456','foreground':'#abcdef','transition':transition}
            validate_content('slides',{'slides':[slide]})
            data,_=export_file({'kind':'slides','title':'Plano','content':{'slides':[slide]}},'pptx')
            deck=Presentation(io.BytesIO(data));self.assertEqual(deck.slides[0]._element.get('show'),'0')
            restored,_=import_file('Plano.pptx',base64.b64encode(data).decode());actual=restored['content']['slides'][0]
            for key in ['hidden','transition','background','foreground']:self.assertEqual(str(actual[key]).lower(),str(slide[key]).lower())
    def test_untrusted_options_rejected(self):
        for page in [None,[],{'font':'Arial; background:url(https://evil.test)'},{'margin':float('nan')},{'orientation':'sideways'},{'fontSize':1000}]:
            with self.subTest(page=page),self.assertRaises(InvalidInput):validate_content('document',{'text':'abc','page':page})
        for key,value in [('hidden','yes'),('background','red;opacity:0'),('foreground',None),('transition','script')]:
            with self.subTest(key=key),self.assertRaises(InvalidInput):validate_content('slides',{'slides':[{'title':'a','body':'b','notes':'',key:value}]})
