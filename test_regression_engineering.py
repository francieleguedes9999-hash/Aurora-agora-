from pathlib import Path
from aurora.regression_engineering import RegressionEngineeringCoordinator

class Mem:
    def __init__(self): self.items=[]
    def remember(self, *a, **kw): self.items.append((a,kw))

class CI:
    def __init__(self, root): self.root=Path(root); self.n=0
    def plan(self, request, depth=2, limit=50): return {'ok':True,'predicted_files':['aurora/foo.py'],'predicted_tests':['tests/test_foo.py'],'fingerprint':'p','target':request}
    def _files(self): self.n+=1; return {'aurora/foo.py':str(self.n)}
    def compare(self,before,after,planned): return {'ok':True,'actual_files':['aurora/foo.py'],'tests':['tests/test_foo.py'],'fingerprint':'c'}

class RI:
    def __init__(self): self.calls=0
    def validate(self, planned, comparison, limit=50):
        self.calls+=1
        return {'ok': self.calls >= 2, 'passed': self.calls >= 2, 'executed':['tests/test_foo.py']}

class Cycle:
    def __init__(self): self.calls=0
    def run(self, *a, **kw): self.calls+=1; return {'ok':True,'attempt':self.calls}

class Agent:
    def __init__(self,tmp):
        class W: root=tmp
        self.workspace=W(); self.change_intelligence=CI(tmp); self.regression_intelligence=RI(); self.cycle=Cycle(); self.memory=Mem(); self.calls=[]
    def _call(self, tool, args):
        self.calls.append((tool,args))
        if tool=='diagnose': return {'ok':False,'file':'aurora/foo.py','error':'regression'}
        if tool=='context_intelligence': return {'ok':True}
        if tool=='impact': return {'ok':True}
        if tool=='knowledge_graph': return {'ok':True}
        return {'ok':True}

def test_regression_is_fed_back_into_correction_loop(tmp_path):
    agent=Agent(tmp_path)
    result=RegressionEngineeringCoordinator(agent, max_attempts=2).run('alterar foo')
    assert result['ok'] is True
    assert result['attempts'] == 2
    assert agent.regression_intelligence.calls == 2
    assert any(x[0]=='diagnose' for x in agent.calls)
    assert (tmp_path/'.aurora/regression_engineering.json').exists()

def test_persistent_regression_is_bounded(tmp_path):
    agent=Agent(tmp_path)
    agent.regression_intelligence.validate=lambda *a,**k: {'ok':False,'passed':False,'executed':['tests/test_foo.py']}
    result=RegressionEngineeringCoordinator(agent, max_attempts=2).run('alterar foo')
    assert result['ok'] is False
    assert result['attempts'] == 2
    assert len([x for x in agent.calls if x[0]=='diagnose']) == 2


class RepairCycle:
    def __init__(self): self.requests=[]
    def run(self, request, *a, **kw):
        self.requests.append(request)
        return {'ok': len(self.requests) >= 2, 'request': request}

def test_regression_retry_executes_repair_request(tmp_path):
    agent=Agent(tmp_path)
    agent.cycle=RepairCycle()
    result=RegressionEngineeringCoordinator(agent, max_attempts=2).run('alterar foo')
    assert result['ok'] is True
    assert len(agent.cycle.requests) == 2
    assert agent.cycle.requests[0] == 'alterar foo'
    assert 'Corrigir a regressão causada por: alterar foo' in agent.cycle.requests[1]
