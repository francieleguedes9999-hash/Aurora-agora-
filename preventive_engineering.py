from __future__ import annotations
import hashlib, json, time, uuid
from pathlib import Path
from typing import Any, Callable


class PreventiveEngineering:
    """Runs cheap preventive checks before a change and validates its aftermath."""
    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'preventive_engineering.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {'history': []}

    def _save(self, state):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    @staticmethod
    def _ok(value: Any) -> bool:
        if isinstance(value, dict):
            if 'ok' in value: return bool(value['ok'])
            if 'passed' in value: return bool(value['passed'])
        return bool(value)

    def preflight(self, target: str, depth: int = 2, limit: int = 50) -> dict[str, Any]:
        prediction = self.agent.predictive_engineering.preflight(target, depth, limit)
        tests = list(dict.fromkeys(prediction.get('preventive_tests', [])))
        return {
            'ok': True,
            'target': target,
            'risk': prediction.get('risk', 'low'),
            'files_to_review': prediction.get('files_to_review', []),
            'preventive_tests': tests,
            'prediction_fingerprint': prediction.get('fingerprint'),
        }

    def run(self, target: str, runner: Callable[[], Any], session_id: str | None = None,
            depth: int = 2, limit: int = 50, run_preventive_tests: bool = True,
            confirmed: bool = False) -> dict[str, Any]:
        target = (target or '').strip()
        if not target:
            return {'ok': False, 'status': 'invalid_request', 'error': 'target vazio'}
        report = {
            'id': uuid.uuid4().hex[:12], 'target': target, 'status': 'running',
            'started_at': time.time(), 'stages': []
        }
        self._save(report)

        plan = self.preflight(target, depth, limit)
        report['stages'].append({'stage': 'preflight', 'ok': True, 'result': plan, 'ts': time.time()})

        guard_engine = getattr(self.agent, 'engineering_guardrails', None)
        guard = (guard_engine.evaluate(target, plan, confirmed=confirmed)
                 if guard_engine is not None else {'ok': True, 'status': 'unavailable', 'reasons': []})
        report['stages'].append({'stage': 'guardrails', 'ok': guard['ok'], 'result': guard, 'ts': time.time()})
        if not guard['ok']:
            report['status'] = 'blocked'
            report['finished_at'] = time.time()
            report['result'] = {'reason': 'guardrail_block', 'guardrails': guard}
            self._finalize(report)
            return {'ok': False, **report}

        if run_preventive_tests and plan['preventive_tests']:
            selected = self.agent.regression_intelligence.run_selected(plan['preventive_tests'])
            report['stages'].append({'stage': 'preventive_tests', 'ok': self._ok(selected), 'result': selected, 'ts': time.time()})
            if not self._ok(selected):
                report['status'] = 'blocked'
                report['finished_at'] = time.time()
                report['result'] = {'reason': 'preventive_test_failed', 'preventive': selected}
                self._finalize(report)
                return {'ok': False, **report}

        before = self.agent.change_intelligence._files()
        try:
            result = runner()
        except Exception as exc:
            result = {'ok': False, 'error': str(exc)}
        after = self.agent.change_intelligence._files()
        planned = self.agent.change_intelligence.plan(target, depth, limit)
        comparison = self.agent.change_intelligence.compare(before, after, planned)
        report['stages'].append({'stage': 'change', 'ok': self._ok(result), 'result': result, 'ts': time.time()})
        report['stages'].append({'stage': 'change_compare', 'ok': True, 'result': comparison, 'ts': time.time()})

        regression = self.agent.regression_intelligence.validate(planned, comparison, limit=limit)
        report['stages'].append({'stage': 'regression', 'ok': self._ok(regression), 'result': regression, 'ts': time.time()})
        report['status'] = 'completed' if self._ok(result) and self._ok(regression) else 'failed'
        report['finished_at'] = time.time()
        report['result'] = {'change': result, 'comparison': comparison, 'regression': regression}
        self._finalize(report)
        return {'ok': report['status'] == 'completed', **report}

    def _finalize(self, report):
        payload = dict(report)
        payload['fingerprint'] = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        state = self._load()
        state.setdefault('history', []).append(payload)
        state['last'] = payload
        state['history'] = state['history'][-100:]
        self._save(state)

    def status(self):
        state = self._load()
        return {'ok': True, 'history': len(state.get('history', [])), 'last': state.get('last')}
