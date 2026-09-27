import json
from pathlib import Path
from types import SimpleNamespace

from aurora.adaptive_cognitive_cycle import AdaptiveCognitiveCycle
from aurora.brain import CognitiveBrain, BrainConfig


class Model:
    provider = 'test'
    def available(self): return True
    def __init__(self): self.calls = 0
    def ask(self, prompt, inputs=None):
        self.calls += 1
        if self.calls == 1:
            return json.dumps({'tool': 'read_file', 'args': {'path': 'x.txt'}})
        return json.dumps({'final': 'concluído'})


class Context:
    def stage_packet(self, *a, **kw): return {'files': [], 'summary': 'ctx'}


class Memory:
    def recent(self, n): return []


class Agent:
    max_steps = 4
    def __init__(self, root):
        self.model = Model(); self.context_intelligence = Context(); self.memory = Memory()
        self.workspace = SimpleNamespace(root=Path(root))
    def available_tools(self): return ['read_file']
    def _call(self, tool, args): return {'ok': True, 'path': args.get('path')}


def test_adaptive_cycle_success_and_persistence(tmp_path):
    a = Agent(tmp_path)
    brain = CognitiveBrain(a, a.model, BrainConfig())
    cycle = AdaptiveCognitiveCycle(brain)
    out = cycle.run('ler arquivo e concluir', session_id='s1')
    assert out['status'] == 'completed'
    assert out['adaptive']['meta_reasoning']['mode'] in {'continue', 'explore'}
    assert (tmp_path / '.aurora' / 'adaptive_cognitive_cycle.json').exists()


def test_adaptive_cycle_bounded(tmp_path):
    a = Agent(tmp_path)
    brain = CognitiveBrain(a, a.model, BrainConfig())
    cycle = AdaptiveCognitiveCycle(brain)
    out = cycle.run('teste', max_steps=1)
    assert out['step'] == 1
    assert out['status'] in {'max_steps', 'completed'}


def test_adaptive_cycle_status(tmp_path):
    a = Agent(tmp_path)
    brain = CognitiveBrain(a, a.model, BrainConfig())
    cycle = AdaptiveCognitiveCycle(brain)
    cycle.run('aprender estratégia')
    status = cycle.status()
    assert status['runs'] == 1
    assert status['brain']['tool_learning'] is not None
