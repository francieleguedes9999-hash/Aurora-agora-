import json
from pathlib import Path
from aurora.autonomous import AutonomousDeveloper

class FakeMemory:
    def remember(self, *args, **kwargs):
        return None

class FakeAgent:
    def __init__(self, root):
        self.workspace = type('W', (), {'root': Path(root)})()
        self.memory = FakeMemory()
        self.calls = 0
    def run_cycle(self, request, session_id=None):
        self.calls += 1
        return {'status': 'completed', 'cycle_id': str(self.calls)}
    def _call(self, tool, args):
        if tool == 'run_tests': return {'passed': True, 'tests': 2}
        raise AssertionError(tool)

def test_autonomous_completes_and_persists(tmp_path):
    a = FakeAgent(tmp_path)
    r = AutonomousDeveloper(a, max_attempts=2).run('criar app')
    assert r['status'] == 'completed'
    assert r['attempts'] == 1
    data = json.loads((tmp_path/'.aurora'/'autonomous.json').read_text())
    assert data['status'] == 'completed'

def test_autonomous_status_without_file(tmp_path):
    a = FakeAgent(tmp_path)
    assert AutonomousDeveloper(a).status() == {'status': 'none'}
