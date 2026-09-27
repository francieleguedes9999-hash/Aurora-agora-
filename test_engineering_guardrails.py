from pathlib import Path
from types import SimpleNamespace
from aurora.engineering_guardrails import EngineeringGuardrails

class Predictive:
    def preflight(self, target, depth=2, limit=50):
        return {'ok': True, 'risk': 'high', 'files_to_review': ['a.py'], 'preventive_tests': ['tests/test_a.py'], 'fingerprint': 'p'}

def make(tmp_path):
    agent = SimpleNamespace(workspace=SimpleNamespace(root=tmp_path), predictive_engineering=Predictive())
    return EngineeringGuardrails(agent)

def test_high_risk_requires_confirmation(tmp_path):
    g = make(tmp_path)
    r = g.preflight('alterar a.py')
    assert not r['ok'] and r['status'] == 'blocked'
    r2 = g.preflight('alterar a.py', confirmed=True)
    assert r2['ok'] and r2['status'] == 'allowed'

def test_destructive_requires_confirmation(tmp_path):
    g = make(tmp_path)
    r = g.preflight('delete production database', confirmed=False)
    assert not r['ok'] and r['destructive']
    assert 'explicit_confirmation' in r['gates']

def test_status_persists(tmp_path):
    g = make(tmp_path)
    g.preflight('alterar a.py', confirmed=True)
    s = g.status()
    assert s['history'] == 1
    assert (Path(tmp_path) / '.aurora' / 'engineering_guardrails.json').exists()
