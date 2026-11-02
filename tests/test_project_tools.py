import copy,unittest
from server.schema import validate_content
from server.store import InvalidInput
class ProjectToolsTest(unittest.TestCase):
    def test_dependencies_dates_and_cycles_validated_server_side(self):
        a={'id':'a','title':'Planejar','due':'2026-11-01','start':'2026-10-30','status':'A fazer'}
        b={'id':'b','title':'Executar','due':'2026-11-03','status':'A fazer','dependsOn':['a']}
        validate_content('board',{'tasks':[a,b]});b['status']='Em andamento'
        with self.assertRaises(InvalidInput):validate_content('board',{'tasks':[a,b]})
        a['status']='Concluído';validate_content('board',{'tasks':[a,b]})
        a['dependsOn']=['b']
        with self.assertRaises(InvalidInput):validate_content('board',{'tasks':[a,b]})
        del a['dependsOn'];a['start']='2026-12-01'
        with self.assertRaises(InvalidInput):validate_content('board',{'tasks':[a,b]})
