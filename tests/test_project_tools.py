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

    def test_baseline_and_capacity_contracts(self):
        from server.project_tools import valid_planning
        baseline={'capturedAt':'2026-01-01T00:00:00Z','tasks':[{'id':'a','title':'Entrega','start':'2026-01-01','due':'2026-01-02','plannedHours':10,'hourlyRate':50,'fixedCost':0}]}
        c={'tasks':[], 'baseline':baseline, 'resources':[{'name':'Ana','dailyHours':0}]}
        validate_content('board',c)
        for hours in (-1,25,True,'8',float('inf')):
            bad=copy.deepcopy(c);bad['resources'][0]['dailyHours']=hours
            self.assertFalse(valid_planning(bad))
        bad=copy.deepcopy(c);bad['resources']*=2;self.assertFalse(valid_planning(bad))
        for key,value in [('due','2026-02-31'),('plannedHours',True),('id',''),('start','2026-02-01')]:
            bad=copy.deepcopy(c);bad['baseline']['tasks'][0][key]=value
            with self.assertRaises(InvalidInput):validate_content('board',bad)
