from pathlib import Path
from types import SimpleNamespace
from aurora.autonomous_engineering import AutonomousEngineering

class Memory:
    def remember(self, *a, **k): return SimpleNamespace()

class FakeAgent:
    max_steps=4
    def __init__(self, root):
        self.workspace=SimpleNamespace(root=str(root)); self.memory=Memory(); self.calls=[]
        self.cycle=SimpleNamespace(run=lambda request, session_id=None: {'status':'completed','request':request})
    def _call(self, tool, args):
        self.calls.append((tool,args))
        if tool=='context_intelligence': return {'ok':True,'context':'ctx'}
        if tool=='knowledge_graph': return {'ok':True,'nodes':3,'edges':2}
        if tool=='impact': return {'ok':True,'files':['aurora/x.py'],'tests':['tests/test_x.py'],'fingerprint':'abc'}
        if tool=='plan': return {'ok':True,'plan':{'steps':[]}}
        if tool=='run_tests': return {'ok':True,'passed':True}
        if tool=='diagnose': return {'ok':True}
        raise AssertionError(tool)

def test_engineering_runs_context_impact_cycle_and_refresh(tmp_path):
    a=FakeAgent(tmp_path); e=AutonomousEngineering(a)
    out=e.run('change x')
    assert out['ok'] is True
    assert [x[0] for x in a.calls] == ['context_intelligence','knowledge_graph','impact','plan','run_tests','knowledge_graph']
    assert e.status()['status']=='completed'

def test_empty_request(tmp_path):
    e=AutonomousEngineering(FakeAgent(tmp_path))
    assert e.run('')['status']=='invalid_request'
