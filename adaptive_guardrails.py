from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from typing import Any


class AdaptiveGuardrails:
    """Adjust engineering guardrails from local project history.

    This is deterministic policy adaptation, not model training. It uses prior
    repair outcomes and recent guardrail decisions to tighten or relax gates.
    """
    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'adaptive_guardrails.json'
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

    def _repair_stats(self, target: str) -> dict[str, Any]:
        memory = getattr(self.agent, 'repair_learning', None)
        cases = []
        if memory is not None and hasattr(memory, '_load'):
            cases = memory._load().get('cases', [])
        target_l = (target or '').lower()
        related = [c for c in cases if target_l and target_l in str(c.get('target', '')).lower()]
        failures = sum(1 for c in related if not c.get('success'))
        successes = sum(1 for c in related if c.get('success'))
        return {'related_cases': len(related), 'failures': failures, 'successes': successes}

    def policy(self, target: str, base: dict[str, Any] | None = None) -> dict[str, Any]:
        base = base or self.agent.predictive_engineering.preflight(target)
        risk = str(base.get('risk', 'low')).lower()
        files = list(base.get('files_to_review', []))
        stats = self._repair_stats(target)
        reasons: list[str] = []
        level = 'normal'
        require_confirmation = risk == 'high'
        require_preventive_tests = bool(files)
        max_files = 25

        if stats['failures'] >= 2:
            level = 'strict'
            require_confirmation = True
            max_files = 10
            reasons.append('há pelo menos 2 falhas anteriores relacionadas')
        elif stats['failures'] == 1:
            level = 'elevated'
            require_confirmation = True
            max_files = 15
            reasons.append('há uma falha anterior relacionada')

        if risk == 'high':
            level = 'strict'
            require_confirmation = True
            reasons.append('risco preditivo alto')
        elif risk == 'medium' and level == 'normal':
            level = 'elevated'
            max_files = 20
            reasons.append('risco preditivo médio')

        if not base.get('preventive_tests') and files:
            require_preventive_tests = True
            reasons.append('impacto possui arquivos mas não há teste preventivo selecionado')

        return {
            'ok': True, 'target': target, 'level': level, 'risk': risk,
            'require_confirmation': require_confirmation,
            'require_preventive_tests': require_preventive_tests,
            'max_files_without_confirmation': max_files,
            'files_to_review': files,
            'preventive_tests': list(base.get('preventive_tests', [])),
            'repair_stats': stats, 'reasons': reasons,
            'base_fingerprint': base.get('fingerprint'),
            'timestamp': time.time(),
        }

    def evaluate(self, target: str, confirmed: bool = False,
                 base: dict[str, Any] | None = None) -> dict[str, Any]:
        policy = self.policy(target, base)
        blocked = False
        gates: list[str] = []
        reasons = list(policy['reasons'])
        if policy['require_confirmation'] and not confirmed:
            blocked = True
            gates.append('adaptive_confirmation')
        if len(policy['files_to_review']) > policy['max_files_without_confirmation'] and not confirmed:
            blocked = True
            gates.append('adaptive_large_change_confirmation')
            reasons.append(f"impacto envolve {len(policy['files_to_review'])} arquivos")
        if policy['require_preventive_tests'] and policy['files_to_review'] and not policy['preventive_tests']:
            blocked = True
            gates.append('adaptive_preventive_tests')
        result = {**policy, 'ok': not blocked, 'status': 'blocked' if blocked else 'allowed',
                  'confirmed': bool(confirmed), 'gates': gates}
        result['fingerprint'] = hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest()
        state = self._load()
        state.setdefault('history', []).append(result)
        state['last'] = result
        state['history'] = state['history'][-100:]
        self._save(state)
        return result

    def preflight(self, target: str, confirmed: bool = False, **kwargs) -> dict[str, Any]:
        return self.evaluate(target, confirmed=confirmed, **kwargs)

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {'ok': True, 'history': len(state.get('history', [])), 'last': state.get('last')}
