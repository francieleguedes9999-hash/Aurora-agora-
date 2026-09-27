from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from typing import Any


class EngineeringGuardrails:
    """Deterministic safety gates for engineering changes.

    Guardrails do not judge code quality; they enforce explicit operational
    conditions before a change is allowed to proceed.
    """
    DESTRUCTIVE_MARKERS = (
        'delete', 'remove', 'drop table', 'drop database', 'truncate',
        'destroy', 'wipe', 'reset database', 'rm -rf', 'format disk',
    )

    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'engineering_guardrails.json'
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

    def evaluate(self, target: str, plan: dict[str, Any] | None = None,
                 require_confirmation_for: tuple[str, ...] = ('high',),
                 confirmed: bool = False,
                 max_files_without_confirmation: int = 25) -> dict[str, Any]:
        target = (target or '').strip()
        plan = plan or self.agent.predictive_engineering.preflight(target)
        risk = str(plan.get('risk', 'low')).lower()
        files = list(plan.get('files_to_review', []))
        lowered = target.lower()
        destructive = any(marker in lowered for marker in self.DESTRUCTIVE_MARKERS)
        reasons: list[str] = []
        gates: list[str] = []
        blocked = False

        if destructive:
            reasons.append('pedido contém marcador de operação potencialmente destrutiva')
            gates.append('explicit_confirmation')
            if not confirmed:
                blocked = True

        if risk in set(require_confirmation_for):
            reasons.append(f'risk={risk}')
            gates.append('risk_confirmation')
            if not confirmed:
                blocked = True

        if len(files) > max_files_without_confirmation:
            reasons.append(f'impacto previsto envolve {len(files)} arquivos')
            gates.append('large_change_confirmation')
            if not confirmed:
                blocked = True

        if not plan.get('preventive_tests') and files:
            reasons.append('não há testes preventivos selecionados para um impacto previsto')
            gates.append('preventive_tests_review')

        result = {
            'ok': not blocked,
            'status': 'blocked' if blocked else 'allowed',
            'target': target,
            'risk': risk,
            'files_to_review': files,
            'preventive_tests': list(plan.get('preventive_tests', [])),
            'destructive': destructive,
            'gates': gates,
            'reasons': reasons,
            'confirmed': bool(confirmed),
            'plan_fingerprint': plan.get('fingerprint'),
            'timestamp': time.time(),
        }
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
