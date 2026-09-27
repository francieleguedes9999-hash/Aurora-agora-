from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any


class RecoveryExecutionEngine:
    """Execute bounded recovery plans under ExecutionMonitor and validation gates."""

    def __init__(self, agent: Any, max_attempts: int = 3):
        self.agent = agent
        self.max_attempts = max(1, int(max_attempts))
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'recovery_execution.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {'history': []}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {'history': []}

    def _save(self, state: dict[str, Any]) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    @staticmethod
    def _ok(value: Any) -> bool:
        if isinstance(value, dict):
            if 'ok' in value:
                return bool(value['ok'])
            if 'passed' in value:
                return bool(value['passed'])
        return bool(value)

    def _record(self, report: dict[str, Any]) -> dict[str, Any]:
        report['finished_at'] = time.time()
        report['fingerprint'] = hashlib.sha256(
            json.dumps(report, sort_keys=True, default=str).encode('utf-8')
        ).hexdigest()
        state = self._load()
        state.setdefault('history', []).append(report)
        state['last'] = report
        state['history'] = state['history'][-100:]
        self._save(state)
        return {'ok': report.get('status') == 'completed', **report}

    def run(self, request: str, *, failure: str = '', diagnosis: dict[str, Any] | None = None,
            session_id: str | None = None, confirmed: bool = False,
            timeout: float | None = None, retries: int = 0,
            max_attempts: int | None = None, research: bool = False,
            max_steps: int | None = None, test_timeout: float | None = None) -> dict[str, Any]:
        request = (request or '').strip()
        if not request:
            return {'ok': False, 'status': 'invalid_request', 'error': 'descrição vazia'}
        attempts = min(self.max_attempts, max(1, int(max_attempts or self.max_attempts)))
        report = {'id': uuid.uuid4().hex[:12], 'request': request, 'status': 'running',
                  'attempts': [], 'started_at': time.time()}
        current_failure, current_diagnosis = failure, diagnosis or {}

        for attempt in range(1, attempts + 1):
            plan = self.agent.engineering_recovery_planner.plan(
                request, failure=current_failure, diagnosis=current_diagnosis,
                confirmed=confirmed)
            entry = {'attempt': attempt, 'plan': plan, 'ts': time.time()}
            report['attempts'].append(entry)
            if not plan.get('ok'):
                report['status'] = 'failed'
                report['result'] = {'stage': 'planning', 'plan': plan}
                return self._record(report)
            selected = plan.get('selected') or {}
            if selected.get('id') == 'request_confirmation' or not plan.get('guardrails', {}).get('ok', True):
                report['status'] = 'blocked'
                report['result'] = {'stage': 'guardrails', 'plan': plan}
                return self._record(report)

            def execute_cycle():
                return self.agent.cycle.run(request, session_id=session_id)

            monitored = self.agent.execution_monitor.run(
                execute_cycle, name=f'recovery:{request[:80]}', timeout=timeout, retries=retries)
            entry['execution'] = monitored
            if not monitored.get('ok'):
                current_failure = str(monitored.get('result') or monitored.get('run', {}).get('status'))
                current_diagnosis = {'error': current_failure, 'stage': 'execution_monitor'}
                continue

            tests = self.agent.execution_monitor.run(
                lambda: self.agent._call('run_tests', {}),
                name='recovery:tests', timeout=test_timeout, retries=0)
            entry['tests'] = tests
            if tests.get('ok') and self._ok(tests.get('result')):
                graph = self.agent._call('knowledge_graph', {'action': 'build', 'force': True})
                entry['graph_refresh'] = graph
                report['status'] = 'completed'
                report['result'] = {'plan': plan, 'execution': monitored, 'tests': tests, 'graph': graph}
                if hasattr(self.agent, 'repair_learning'):
                    self.agent.repair_learning.record(
                        current_failure or 'recovery', current_diagnosis,
                        str(selected.get('action', 'recovery')), request, True,
                        {'engine': 'recovery_execution', 'attempt': attempt})
                return self._record(report)

            current_failure = str(tests.get('result') or tests.get('run', {}).get('status'))
            current_diagnosis = self.agent._call('diagnose', {'result': tests})
            entry['diagnosis'] = current_diagnosis
            if hasattr(self.agent, 'repair_learning'):
                self.agent.repair_learning.record(
                    current_failure, current_diagnosis,
                    str(selected.get('action', 'recovery')), request, False,
                    {'engine': 'recovery_execution', 'attempt': attempt})

        report['status'] = 'failed'
        report['result'] = {'reason': 'recovery_attempts_exhausted'}
        return self._record(report)

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {'ok': True, 'history': len(state.get('history', [])), 'last': state.get('last')}
