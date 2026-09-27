import json
from pathlib import Path
from types import SimpleNamespace
from aurora.brain import CognitiveBrain, BrainConfig
from aurora.brain_predictive_recovery import PredictiveCognitiveRecovery
from aurora.brain_learning import BrainToolLearning


def test_predicts_repeated_failure_as_high_risk(tmp_path):
    learning = BrainToolLearning(tmp_path)
    learning.observe('corrigir testes', [
        {'action': {'tool': 'run_tests'}, 'result': {'ok': False, 'passed': False}},
        {'action': {'tool': 'run_tests'}, 'result': {'ok': False, 'passed': False}},
    ], False)
    p = PredictiveCognitiveRecovery(tmp_path, learning)
    out = p.predict('corrigir testes', [
        {'action': {'tool': 'run_tests'}, 'result': {'ok': False, 'passed': False}},
        {'action': {'tool': 'run_tests'}, 'result': {'ok': False, 'passed': False}},
    ])
    assert out['risk'] == 'high'
    assert 'run_tests' in out['risky_tools']


def test_low_risk_has_no_warning(tmp_path):
    p = PredictiveCognitiveRecovery(tmp_path)
    out = p.predict('criar arquivo')
    assert out['risk'] == 'low'
    assert p.status()['warnings'] == 0


def test_brain_prompt_contains_prediction(tmp_path):
    class Model:
        provider='test'
        def available(self): return True
        def ask(self, prompt, inputs=None): return json.dumps({'final':'ok'})
    class Context:
        def stage_packet(self,*a,**kw): return {}
    agent=SimpleNamespace(model=Model(), workspace=SimpleNamespace(root=Path(tmp_path)), context_intelligence=Context(), memory=SimpleNamespace(recent=lambda n:[]), available_tools=lambda:['read_file'])
    brain=CognitiveBrain(agent, agent.model, BrainConfig())
    payload=json.loads(brain.build_prompt('criar arquivo'))
    assert 'predictive_recovery' in payload
    assert payload['predictive_recovery']['risk'] == 'low'
