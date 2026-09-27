from pathlib import Path

from aurora.agent import Agent
from aurora.adaptive_cognitive_cycle import AdaptiveCognitiveCycle
from aurora.brain import CognitiveBrain


class DummyModel:
    provider = 'dummy'
    def available(self): return True
    def ask(self, prompt, inputs=None):
        return '{"final":"ok"}'


def make_agent(tmp_path):
    a = Agent.__new__(Agent)
    a.workspace = type('W', (), {'root': tmp_path})()
    a.model = DummyModel()
    a.max_steps = 3
    a.memory = type('M', (), {'recent': lambda self, n: []})()
    a.researcher = type('R', (), {'available': lambda self: True})()
    a.context_intelligence = type('C', (), {'stage_packet': lambda self, *args, **kwargs: {'ok': True}})()
    a.training_lab = type('T', (), {'context': lambda self, *args, **kwargs: '', 'status': lambda self: {}})()
    a.available_tools = lambda: ['research', 'run_command', 'run_tests']
    a._call = lambda tool, args: {'ok': True}
    a.recovery_execution = None
    return a


def test_brain_can_enable_research_context(tmp_path):
    a = make_agent(tmp_path)
    b = CognitiveBrain(a, a.model)
    prompt = b.build_prompt('crie um app e pesquise como fazer a integração', research=True)
    assert '"research_mode": true' in prompt
    assert '"research_available": true' in prompt


def test_adaptive_cycle_research_flag_is_persisted(tmp_path):
    a = make_agent(tmp_path)
    b = CognitiveBrain(a, a.model)
    cycle = AdaptiveCognitiveCycle(b)
    result = cycle.run('teste', max_steps=1, research=True, recovery=False)
    assert result['status'] == 'completed'
    assert result['adaptive']['research_enabled'] is True
