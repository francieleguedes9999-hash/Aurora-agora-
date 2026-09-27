from pathlib import Path
from aurora.research_execution import ResearchExecution

class WS:
    def __init__(self, root): self.root = Path(root)

class Cycle:
    def __init__(self): self.calls=[]
    def run(self, request, session_id=None): self.calls.append(request); return {'ok': True, 'request': request}

class Agent:
    def __init__(self, tmp):
        self.workspace=WS(tmp); self.cycle=Cycle()
        self.tests=0
    def _call(self, tool, args):
        if tool == 'research_plan':
            return {'ok': True, 'steps': [
                {'id':1,'stage':'understand','action':'entender'},
                {'id':2,'stage':'implementation','action':'implementar'},
            ]}
        if tool == 'run_tests': self.tests += 1; return {'ok': True, 'passed': True}
        if tool == 'diagnose': return {'ok': True}
        raise AssertionError(tool)

def test_executes_plan_in_verified_stages(tmp_path):
    a=Agent(tmp_path); e=ResearchExecution(a)
    r=e.run('criar app', max_stages=2)
    assert r['ok'] is True
    assert r['status']=='completed'
    assert len(r['stages'])==2
    assert a.tests==2
    assert len(a.cycle.calls)==2
    assert e.status()['runs']==1
