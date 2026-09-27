from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable


class SelfHealingGuardrails:
    """Turn guardrail blocks into bounded, safer recovery attempts.

    A blocked operation is never allowed to bypass confirmation or destructive
    gates automatically. When a caller supplies a safe alternative runner,
    the coordinator can execute that alternative and validate its result.
    """

    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'self_healing_guardrails.json'
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

    def alternatives(self, target: str, guard: dict[str, Any]) -> list[dict[str, Any]]:
        gates = set(guard.get('gates', []))
        options: list[dict[str, Any]] = []
        if 'large_change_confirmation' in gates or 'adaptive_large_change_confirmation' in gates:
            options.append({'id': 'narrow_scope', 'action': 'reduce_scope',
                            'reason': 'reduzir o conjunto de arquivos afetados antes de tentar novamente',
                            'automatic': True})
        if 'adaptive_preventive_tests' in gates or 'preventive_tests_review' in gates:
            options.append({'id': 'add_preventive_tests', 'action': 'prepare_tests',
                            'reason': 'preparar testes preventivos antes da alteração',
                            'automatic': True})
        if 'risk_confirmation' in gates or 'adaptive_confirmation' in gates or 'explicit_confirmation' in gates:
            options.append({'id': 'request_confirmation', 'action': 'await_confirmation',
                            'reason': 'a operação exige confirmação explícita e não será contornada',
                            'automatic': False})
        return options

    def run(self, target: str, runner: Callable[[], Any],
            alternative_runner: Callable[[dict[str, Any]], Any] | None = None,
            confirmed: bool = False, max_recovery_attempts: int = 1) -> dict[str, Any]:
        target = (target or '').strip()
        if not target:
            return {'ok': False, 'status': 'invalid_request', 'error': 'target vazio'}
        max_recovery_attempts = max(0, int(max_recovery_attempts))
        report: dict[str, Any] = {
            'id': uuid.uuid4().hex[:12], 'target': target,
            'status': 'running', 'attempts': [], 'started_at': time.time()
        }

        adaptive = getattr(self.agent, 'adaptive_guardrails', None)
        engineering = getattr(self.agent, 'engineering_guardrails', None)
        base_guard = engineering.evaluate(target, confirmed=confirmed) if engineering else {'ok': True, 'status': 'allowed', 'gates': [], 'reasons': []}
        adaptive_guard = adaptive.evaluate(target, confirmed=confirmed) if adaptive else {'ok': True, 'status': 'allowed', 'gates': [], 'reasons': []}
        guard = dict(adaptive_guard)
        guard['ok'] = bool(base_guard.get('ok', True)) and bool(adaptive_guard.get('ok', True))
        guard['status'] = 'allowed' if guard['ok'] else 'blocked'
        guard['gates'] = list(dict.fromkeys(list(base_guard.get('gates', [])) + list(adaptive_guard.get('gates', []))))
        guard['reasons'] = list(dict.fromkeys(list(base_guard.get('reasons', [])) + list(adaptive_guard.get('reasons', []))))
        guard['destructive'] = bool(base_guard.get('destructive', False))
        report['attempts'].append({'stage': 'guardrails', 'ok': bool(guard.get('ok')), 'result': guard, 'ts': time.time()})

        if not guard.get('ok'):
            options = self.alternatives(target, guard)
            report['alternatives'] = options
            if alternative_runner is None or max_recovery_attempts == 0:
                report['status'] = 'blocked'
                report['result'] = {'reason': 'guardrail_block', 'guardrails': guard, 'alternatives': options}
                return self._finalize(report)

            for attempt in range(1, max_recovery_attempts + 1):
                automatic = [o for o in options if o.get('automatic')]
                if not automatic:
                    break
                option = automatic[min(attempt - 1, len(automatic) - 1)]
                try:
                    result = alternative_runner(option)
                except Exception as exc:
                    result = {'ok': False, 'error': str(exc)}
                report['attempts'].append({'stage': 'recovery', 'attempt': attempt,
                                          'option': option, 'ok': self._ok(result),
                                          'result': result, 'ts': time.time()})
                if self._ok(result):
                    # Re-check the guardrail after the alternative has prepared a
                    # safer state. Confirmation/destructive gates remain enforced.
                    new_base = engineering.evaluate(target, confirmed=confirmed) if engineering else {'ok': True}
                    new_adaptive = adaptive.evaluate(target, confirmed=confirmed) if adaptive else {'ok': True}
                    new_guard = dict(new_adaptive)
                    new_guard['ok'] = bool(new_base.get('ok', True)) and bool(new_adaptive.get('ok', True))
                    new_guard['status'] = 'allowed' if new_guard['ok'] else 'blocked'
                    new_guard['gates'] = list(dict.fromkeys(list(new_base.get('gates', [])) + list(new_adaptive.get('gates', []))))
                    new_guard['reasons'] = list(dict.fromkeys(list(new_base.get('reasons', [])) + list(new_adaptive.get('reasons', []))))
                    new_guard['destructive'] = bool(new_base.get('destructive', False))
                    report['attempts'].append({'stage': 'recheck', 'ok': bool(new_guard.get('ok', True)),
                                               'result': new_guard, 'ts': time.time()})
                    if new_guard.get('ok', True):
                        guard = new_guard
                        break
            else:
                guard = guard

            if not guard.get('ok'):
                report['status'] = 'blocked'
                report['result'] = {'reason': 'recovery_did_not_clear_guardrails',
                                    'guardrails': guard, 'alternatives': options}
                return self._finalize(report)

        try:
            result = runner()
        except Exception as exc:
            result = {'ok': False, 'error': str(exc)}
        report['attempts'].append({'stage': 'execution', 'ok': self._ok(result),
                                   'result': result, 'ts': time.time()})
        report['status'] = 'completed' if self._ok(result) else 'failed'
        report['result'] = result
        return self._finalize(report)

    def _finalize(self, report: dict[str, Any]) -> dict[str, Any]:
        report['finished_at'] = time.time()
        payload = dict(report)
        payload['fingerprint'] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        state = self._load()
        state.setdefault('history', []).append(payload)
        state['last'] = payload
        state['history'] = state['history'][-100:]
        self._save(state)
        return {'ok': report['status'] == 'completed', **report, 'fingerprint': payload['fingerprint']}

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {'ok': True, 'history': len(state.get('history', [])), 'last': state.get('last')}
