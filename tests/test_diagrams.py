import unittest
from server.schema import validate_content
from server.store import InvalidInput
class DiagramTest(unittest.TestCase):
    def test_shape_and_label_contract_is_compatible_and_bounded(self):
        c={'nodes':['A','B'],'positions':[{'x':0,'y':0},{'x':300,'y':0}], 'edges':[{'from':0,'to':1,'label':'Sim'}]}
        validate_content('diagram',c)
        c['shapes']=['decision','database'];validate_content('diagram',c)
        for shapes in (['process'],['process','arbitrary'],[['process'],'document']):
            with self.assertRaises(InvalidInput):validate_content('diagram',dict(c,shapes=shapes))
        with self.assertRaises(InvalidInput):validate_content('diagram',dict(c,edges=[{'from':0,'to':1,'label':'x'*101}]))
