from pathlib import Path
import tempfile

from aurora.execution_monitor import ExecutionMonitor
from aurora.recovery_execution import RecoveryExecutionEngine


class Workspace:
    def __init__(self, root): self.root = root


class Planner:
    def plan(self, target, **kwargs):
        return {'ok': True, 'guardrails': {'ok': True}, 'selected': {'id': 'targeted_tests', 'action': 'run_targeted_tests'}}


class Cycle:
    def run(self, request, session_id=None):
        return {'ok': True, 'request': request}


class Graph:
    def build(self, **kwargs): return {'ok': True}


class Repair:
    def record(self, *args, **kwargs): return {'id': 'x'}


class Agent:
    def __init__(self, root):
        self.workspace = Workspace(root)
        self.engineering_recovery_planner = Planner()
        self.execution_monitor = ExecutionMonitor(root)
        self.cycle = Cycle()
        self.repair_learning = Repair()
        self._graph = Graph()
    def _call(self, tool, args):
        if tool == 'run_tests': return {'ok': True, 'passed': True}
        if tool == 'knowledge_graph': return self._graph.build(**args)
        if tool == 'diagnose': return {'ok': False, 'error': 'x'}
        raise AssertionError(tool)


def test_recovery_execution_success():
    with tempfile.TemporaryDirectory() as d:
        result = RecoveryExecutionEngine(Agent(d)).run('repair app', max_attempts=1)
        assert result['ok'] is True
        assert result['status'] == 'completed'
        assert result['attempts'][0]['execution']['ok'] is True
        assert result['attempts'][0]['tests']['ok'] is True


def test_recovery_execution_requires_confirmation():
    class BlockedPlanner(Planner):
        def plan(self, target, **kwargs):
            return {'ok': True, 'guardrails': {'ok': False}, 'selected': {'id': 'request_confirmation'}}
    with tempfile.TemporaryDirectory() as d:
        a = Agent(d); a.engineering_recovery_planner = BlockedPlanner()
        result = RecoveryExecutionEngine(a).run('dangerous change', max_attempts=2)
        assert result['ok'] is False
        assert result['status'] == 'blocked'


def test_execution_monitor_timeout_is_recorded():
    import time
    with tempfile.TemporaryDirectory() as d:
        m = ExecutionMonitor(d)
        result = m.run(lambda: (time.sleep(0.05), {'ok': True})[1], timeout=0.01)
        assert result['ok'] is False
        assert result['run']['status'] == 'timeout'
