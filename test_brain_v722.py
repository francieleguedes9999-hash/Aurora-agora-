import json
from pathlib import Path
from types import SimpleNamespace
from aurora.brain import CognitiveBrain, BrainConfig
from aurora.brain_memory import BrainMemory

class Model:
    provider='test'
    def available(self): return True
    def ask(self, prompt, inputs=None): return json.dumps({'final':'ok'})

class Context:
    def stage_packet(self, *a, **kw): return {'files': [], 'summary': 'ctx'}

class Memory:
    def recent(self, n): return []

class Agent:
    max_steps=3
    model=Model()
    context_intelligence=Context()
    memory=Memory()
    workspace=SimpleNamespace(root=Path('/tmp/aurora-v722-test'))
    def available_tools(self): return ['brain_memory']
    def _call(self, tool, args): return {'ok': True}

def test_brain_persists_session(tmp_path):
    a=Agent(); a.workspace.root=tmp_path
    b=CognitiveBrain(a, a.model, BrainConfig())
    out=b.run('hello', session_id='s1')
    assert out['status']=='completed'
    store=BrainMemory(tmp_path)
    assert store.get('s1')['turns']

def test_brain_memory_status(tmp_path):
    m=BrainMemory(tmp_path)
    assert m.status()['sessions']==0

def test_parse_fenced_json():
    assert CognitiveBrain.parse_action('```json\n{"final":"x"}\n```')['final']=='x'
