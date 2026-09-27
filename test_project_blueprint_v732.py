from pathlib import Path
from aurora.project_blueprint import ProjectBlueprint

class WS:
    def __init__(self, root): self.root = Path(root)

class Spec:
    def build(self, request):
        return type('S', (), {'name':'Teste','description':request,'kind':'web','frontend':'html','backend':'python','database':'none','auth':False,'screens':[],'components':[],'theme':{},'entities':[],'endpoints':[],'user_flows':[],'acceptance_criteria':[],'assumptions':[]})()

class Decomp:
    def decompose(self, request, reuse=False, replace=True):
        return {'decomposition': {'tasks': [
            {'id':'t1','title':'Implementar','stage':'implementation','depends_on':[],'acceptance':['feito'],'context_query':request}
        ]}}

def test_blueprint_builds_whole_project(tmp_path):
    a=type('A', (), {'workspace':WS(tmp_path), 'app_spec':Spec(), 'task_decomposer':Decomp()})()
    b=ProjectBlueprint(a)
    r=b.build('criar aplicativo de tarefas', research=True)
    assert r['ok']
    assert r['blueprint']['spec']['name']=='Teste'
    assert r['blueprint']['tasks'][0]['id']=='bp_spec'
    assert 'bp_research' in r['blueprint']['gates']
    assert r['blueprint']['tasks'][-1]['depends_on']
    assert b.status()['tasks'] >= 3
