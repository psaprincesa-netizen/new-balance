import copy,unittest
from server.forms import form_schema,validate_answers,score_response
from server.schema import validate_content
from server.store import InvalidInput
class FormConditionsTest(unittest.TestCase):
    def setUp(self):
        self.content={'questions':['Atender?','Categoria','Detalhes'],'responses':[],'quiz':True,'fields':[
            {'type':'choice','required':True,'options':['Sim','Não']},
            {'type':'choice','required':True,'options':['A','B'],'correct':'A','points':5,'showWhen':{'question':0,'value':'Sim'}},
            {'type':'text','required':True,'options':[],'correct':'ok','points':10,'showWhen':{'question':1,'value':'A'}}]}
    def answer(self,answers):return validate_answers(self.content,answers,form_schema(self.content)['schema_id'])
    def test_hidden_required_answers_are_removed_and_not_graded(self):
        validate_content('form',self.content)
        self.assertEqual(self.answer(['Não','A','forged']),['Não','',''])
        self.assertEqual(score_response(self.content,['Não','A','ok']),{'score':0,'total':0})
        self.assertEqual(self.answer(['Sim','A','ok']),['Sim','A','ok'])
        self.assertEqual(score_response(self.content,['Sim','A','ok']),{'score':15,'total':15})
        with self.assertRaises(InvalidInput):self.answer(['Sim','A',''])
    def test_rules_are_public_but_keys_remain_private_and_schema_changes(self):
        schema=form_schema(self.content)
        self.assertIn('showWhen',schema['fields'][1]);self.assertNotIn('correct',schema['fields'][1]);self.assertNotIn('points',schema['fields'][1])
        self.content['fields'][1]['showWhen']['value']='Não'
        self.assertNotEqual(schema['schema_id'],form_schema(self.content)['schema_id'])
    def test_invalid_forward_self_and_nonchoice_conditions_rejected(self):
        for condition in [{'question':2,'value':'Sim'},{'question':1,'value':'A'},{'question':True,'value':'Sim'},{'question':0,'value':'Desconhecido'}]:
            bad=copy.deepcopy(self.content);bad['fields'][1]['showWhen']=condition
            with self.assertRaises(InvalidInput):validate_content('form',bad)
        bad=copy.deepcopy(self.content);bad['fields'][0]['type']='text'
        with self.assertRaises(InvalidInput):validate_content('form',bad)
