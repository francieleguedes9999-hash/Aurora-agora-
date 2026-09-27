from pathlib import Path
from aurora.change_intelligence import ChangeIntelligence
from aurora.regression_intelligence import RegressionIntelligence

class FakeImpact:
    def analyze(self, target, depth=2, limit=50):
        return {'files': ['aurora/foo.py'], 'tests': ['tests/test_foo.py'], 'fingerprint': 'impact'}

class FakeRunner:
    def __init__(self): self.calls=[]
    def run(self, command):
        self.calls.append(command)
        return {'ok': True, 'passed': True}

def test_selects_predicted_and_changed_test(tmp_path):
    ci = ChangeIntelligence(tmp_path, FakeImpact())
    ri = RegressionIntelligence(tmp_path, ci, FakeRunner())
    planned = ci.plan('foo')
    selected = ri.select(planned, {'actual_files': ['tests/test_changed.py']})
    assert selected['tests'] == ['tests/test_changed.py', 'tests/test_foo.py']

def test_validate_runs_targeted_tests(tmp_path):
    ci = ChangeIntelligence(tmp_path, FakeImpact())
    runner = FakeRunner()
    ri = RegressionIntelligence(tmp_path, ci, runner)
    result = ri.validate({'fingerprint':'p','predicted_tests':['tests/test_foo.py']}, {'fingerprint':'c'})
    assert result['ok']
    assert runner.calls == ['python -m pytest -q tests/test_foo.py']
    assert ri.status()['history'] == 1

def test_stops_on_first_regression(tmp_path):
    ci = ChangeIntelligence(tmp_path, FakeImpact())
    runner = FakeRunner()
    runner.run = lambda command: {'ok': False if command.endswith('one.py') else True}
    ri = RegressionIntelligence(tmp_path, ci, runner)
    result = ri.run_selected(['tests/one.py', 'tests/two.py'])
    assert result['ok'] is False
    assert result['executed'] == ['tests/one.py']
