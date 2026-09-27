from pathlib import Path
from types import SimpleNamespace
from aurora.adaptive_guardrails import AdaptiveGuardrails

class Predictive:
    def preflight(self, target):
        return {'ok': True, 'risk': 'low', 'files_to_review': ['a.py'], 'preventive_tests': ['tests/test_a.py'], 'fingerprint': 'p'}

class Memory:
    def __init__(self, cases): self.cases = cases
    def _load(self): return {'cases': self.cases}

def make(tmp_path, cases=()):
    return AdaptiveGuardrails(SimpleNamespace(workspace=SimpleNamespace(root=tmp_path), predictive_engineering=Predictive(), repair_learning=Memory(list(cases))))

def test_normal_policy_allows_without_confirmation(tmp_path):
    g = make(tmp_path)
    r = g.preflight('alterar a.py')
    assert r['ok'] and r['level'] == 'normal'

def test_one_related_failure_elevates(tmp_path):
    g = make(tmp_path, [{'target': 'alterar a.py', 'success': False}])
    r = g.preflight('alterar a.py')
    assert not r['ok'] and r['level'] == 'elevated'
    assert 'adaptive_confirmation' in r['gates']

def test_two_failures_strict_and_confirmation_allows(tmp_path):
    cases = [{'target': 'alterar a.py', 'success': False}, {'target': 'alterar a.py', 'success': False}]
    g = make(tmp_path, cases)
    r = g.preflight('alterar a.py')
    assert not r['ok'] and r['level'] == 'strict'
    r2 = g.preflight('alterar a.py', confirmed=True)
    assert r2['ok']

def test_history_persists(tmp_path):
    g = make(tmp_path)
    g.preflight('alterar a.py')
    assert g.status()['history'] == 1
    assert (Path(tmp_path) / '.aurora' / 'adaptive_guardrails.json').exists()
