import json
from pathlib import Path
from aurora.autonomous_engineering import AutonomousEngineering

class Memory:
    def __init__(self): self.items=[]
    def remember(self,*args,**kwargs): self.items.append((args,kwargs))
class FakeCycle:
    def __init__(self): self.calls=0
    def run(self, request, session_id=None):
        self.calls += 1
        return {'ok': True, 'attempt': self.calls}
class Agent:
    def __init__(self, root):
        self.workspace=type('W',(),{'root':Path(root)})()
        self.max_steps=3; self.memory=Memory(); self.cycle=FakeCycle(); self.calls=[]
    def _call(self, tool, args):
        self.calls.append((tool,args))
        if tool == 'context_intelligence': return {'ok': True, 'stage': args['stage']}
        if tool == 'knowledge_graph': return {'ok': True}
        if tool == 'impact': return {'ok': True, 'files':['src/app.py'], 'preflight': args.get('action')=='preflight'}
        if tool == 'plan': return {'ok': True, 'plan': {}}
        if tool == 'run_tests': return {'passed': self.cycle.calls >= 2, 'stderr': '' if self.cycle.calls >= 2 else 'File "src/app.py", line 4\nTypeError: bad type'}
        if tool == 'diagnose': return {'ok': False, 'kind':'type', 'file':'src/app.py', 'line':4, 'message':'TypeError: bad type'}
        raise AssertionError(tool)

def test_repair_prepares_context_and_impact(tmp_path):
    a=Agent(tmp_path)
    r=AutonomousEngineering(a, max_attempts=2).run('corrigir app')
    assert r['ok'] is True
    assert any(t=='context_intelligence' and x.get('stage')=='correction' for t,x in a.calls)
    assert any(t=='impact' and x.get('action')=='preflight' and x.get('target')=='src/app.py' for t,x in a.calls)
    assert len(a.memory.items)==1
    data=json.loads((tmp_path/'.aurora'/'engineering.json').read_text())
    assert any(s['stage']=='repair_impact_1' for s in data['stages'])
