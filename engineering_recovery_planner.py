from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class EngineeringRecoveryPlanner:
    """Plan bounded recovery strategies before executing a recovery.

    This is deterministic orchestration: it ranks available recovery options
    from local risk, guardrails and repair history. It does not silently bypass
    confirmation or destructive-operation gates.
    """

    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'engineering_recovery_planner.json'
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
    def _score(option: dict[str, Any], guard: dict[str, Any], predictive: dict[str, Any]) -> tuple[int, int, str]:
        # Lower cost and lower operational risk rank earlier. Confirmation is
        # never treated as an automatic strategy.
        cost = int(option.get('cost', 1))
        risk = int(option.get('risk', 1))
        if guard.get('destructive') and option.get('automatic', True):
            risk += 100
        return (risk, cost, str(option.get('id', '')))

    def plan(self, target: str, failure: str = '', diagnosis: dict[str, Any] | None = None,
             depth: int = 2, limit: int = 50, max_options: int = 8,
             confirmed: bool = False) -> dict[str, Any]:
        target = (target or '').strip()
        if not target:
            return {'ok': False, 'status': 'invalid_request', 'error': 'target vazio'}

        predictive = self.agent.predictive_engineering.preflight(target, depth=depth, limit=limit)
        guard = self.agent.engineering_guardrails.evaluate(target, confirmed=confirmed)
        adaptive = self.agent.adaptive_guardrails.evaluate(target, confirmed=confirmed)
        gates = list(dict.fromkeys(list(guard.get('gates', [])) + list(adaptive.get('gates', []))))
        reasons = list(dict.fromkeys(list(guard.get('reasons', [])) + list(adaptive.get('reasons', []))))
        destructive = bool(guard.get('destructive', False))

        options: list[dict[str, Any]] = []
        if not destructive:
            options.append({'id': 'narrow_scope', 'action': 'reduce_scope', 'automatic': True,
                            'cost': 1, 'risk': 1,
                            'reason': 'reduzir o conjunto de arquivos afetados antes de recuperar'})
            options.append({'id': 'targeted_tests', 'action': 'run_targeted_tests', 'automatic': True,
                            'cost': 1, 'risk': 1,
                            'tests': predictive.get('preventive_tests', []),
                            'reason': 'executar testes preventivos antes de uma nova alteração'})
            options.append({'id': 'reuse_known_repair', 'action': 'reuse_repair_pattern', 'automatic': True,
                            'cost': 2, 'risk': 2,
                            'reason': 'usar padrão de reparo relacionado já registrado'})
            options.append({'id': 'split_change', 'action': 'split_change', 'automatic': True,
                            'cost': 2, 'risk': 2,
                            'reason': 'dividir a recuperação em alterações menores'})
        # This is deliberately non-automatic: confirmation cannot be bypassed.
        if gates or destructive:
            options.append({'id': 'request_confirmation', 'action': 'await_confirmation', 'automatic': False,
                            'cost': 0, 'risk': 0,
                            'reason': 'aguardar confirmação explícita para os gates ativos'})

        options.sort(key=lambda item: self._score(item, guard, predictive))
        options = options[:max(1, int(max_options))]
        selected = next((o for o in options if o.get('automatic')), None)
        if destructive or any(g in {'explicit_confirmation', 'risk_confirmation', 'adaptive_confirmation'} for g in gates):
            selected = next((o for o in options if o['id'] == 'request_confirmation'), selected)

        payload = {
            'ok': True, 'status': 'planned', 'target': target,
            'failure': failure, 'diagnosis': diagnosis or {},
            'risk': predictive.get('risk', 'low'),
            'predictions': predictive.get('predictions', []),
            'preventive_tests': predictive.get('preventive_tests', []),
            'guardrails': {'gates': gates, 'reasons': reasons, 'destructive': destructive,
                           'ok': bool(guard.get('ok', True) and adaptive.get('ok', True))},
            'options': options, 'selected': selected,
            'timestamp': time.time(),
        }
        payload['fingerprint'] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        state = self._load()
        state.setdefault('history', []).append(payload)
        state['last'] = payload
        state['history'] = state['history'][-100:]
        self._save(state)
        return payload

    def alternatives(self, target: str, **kwargs: Any) -> dict[str, Any]:
        result = self.plan(target, **kwargs)
        return {'ok': result.get('ok', False), 'target': target,
                'options': result.get('options', []), 'selected': result.get('selected'),
                'fingerprint': result.get('fingerprint')}

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {'ok': True, 'history': len(state.get('history', [])), 'last': state.get('last')}
