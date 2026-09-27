import json
from pathlib import Path
from types import SimpleNamespace

from aurora.adaptive_cognitive_cycle import AdaptiveCognitiveCycle
from aurora.brain import CognitiveBrain, BrainConfig


class FailingModel:
    provider = 'test'
    def available(self): return True
    def __init__(self): self.calls = 0
    def ask(self, prompt, inputs=None):
        self.calls += 1
        return json.dumps({'tool': 'run_tests', 'args': {}})


class Context:
    def stage_packet(self, *a, **kw): return {'files': [], 'summary': 'ctx'}


class Memory:
    def recent(self, n): return []


class Recovery:
    def __init__(self): self.calls = []
    def run(self, request, **kwargs):
        self.calls.append((request, kwargs))
        return {'ok': True, 'status': 'completed', 'attempts': 1}


class Agent:
    max_steps = 4
    def __init__(self, root):
        self.model = FailingModel()
        self.context_intelligence = Context()
        self.memory = Memory()
        self.workspace = SimpleNamespace(root=Path(root))
        self.recovery_execution = Recovery()
    def available_tools(self): return ['run_tests']
    def _call(self, tool, args): return {'passed': False, 'ok': False, 'error': 'teste falhou'}


def test_adaptive_cycle_triggers_recovery_after_repeated_failure(tmp_path):
    agent = Agent(tmp_path)
    brain = CognitiveBrain(agent, agent.model, BrainConfig())
    cycle = AdaptiveCognitiveCycle(brain)
    out = cycle.run('corrigir os testes', max_steps=2)
    assert out['status'] == 'max_steps'
    assert out['adaptive']['meta_reasoning']['mode'] == 'switch'
    assert out['adaptive']['recovery']['status'] == 'completed'
    assert len(agent.recovery_execution.calls) == 1


def test_adaptive_cycle_can_disable_recovery(tmp_path):
    agent = Agent(tmp_path)
    brain = CognitiveBrain(agent, agent.model, BrainConfig())
    cycle = AdaptiveCognitiveCycle(brain)
    out = cycle.run('corrigir os testes', max_steps=2, recovery=False)
    assert out['adaptive']['meta_reasoning']['mode'] == 'switch'
    assert out['adaptive']['recovery'] is None
    assert agent.recovery_execution.calls == []
