from pathlib import Path
from types import SimpleNamespace
from aurora.preventive_engineering import PreventiveEngineering


class DummyChange:
    def __init__(self): self.calls = 0
    def _files(self): return {'app.py': 'a'}
    def plan(self, target, depth=2, limit=50): return {'ok': True, 'target': target, 'predicted_files': ['app.py'], 'predicted_tests': [], 'fingerprint': 'p'}
    def compare(self, before, after, planned): return {'ok': True, 'actual_files': [], 'tests': [], 'fingerprint': 'c'}

class DummyPredictive:
    def preflight(self, target, depth=2, limit=50): return {'ok': True, 'target': target, 'risk': 'low', 'files_to_review': ['app.py'], 'preventive_tests': [], 'fingerprint': 'x'}

class DummyRegression:
    def run_selected(self, tests): return {'ok': True, 'passed': True, 'selected': tests, 'executed': tests}
    def validate(self, planned, comparison, limit=50): return {'ok': True, 'passed': True}

class DummyWorkspace: root = None


def make(tmp_path):
    agent = SimpleNamespace(workspace=SimpleNamespace(root=tmp_path), predictive_engineering=DummyPredictive(), change_intelligence=DummyChange(), regression_intelligence=DummyRegression())
    return agent, PreventiveEngineering(agent)


def test_preflight(tmp_path):
    agent, pe = make(tmp_path)
    r = pe.preflight('alterar app')
    assert r['ok'] and r['risk'] == 'low'


def test_run_success(tmp_path):
    agent, pe = make(tmp_path)
    r = pe.run('alterar app', lambda: {'ok': True})
    assert r['ok'] and r['status'] == 'completed'
    assert (Path(tmp_path) / '.aurora' / 'preventive_engineering.json').exists()


def test_run_failure(tmp_path):
    agent, pe = make(tmp_path)
    r = pe.run('alterar app', lambda: {'ok': False, 'error': 'boom'})
    assert not r['ok'] and r['status'] == 'failed'
