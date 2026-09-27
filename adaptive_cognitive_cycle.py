from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .brain import CognitiveBrain


class AdaptiveCognitiveCycle:
    """Unified bounded cognitive controller.

    Combines the brain's execution history with persistent tool learning and
    meta-reasoning. It is an orchestration layer, not model training.
    """
    def __init__(self, brain: CognitiveBrain):
        self.brain = brain
        self.root = Path(brain.agent.workspace.root)
        self.path = self.root / '.aurora' / 'adaptive_cognitive_cycle.json'
        self.data: dict[str, Any] = {'runs': [], 'strategy_switches': 0}
        self._load()

    def _load(self) -> None:
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(value, dict):
                self.data.update(value)
        except (OSError, ValueError, TypeError):
            pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    def run(self, request: str, session_id: str | None = None,
            max_steps: int | None = None,
            inputs: list[dict[str, Any]] | None = None,
            research: bool = True,
            recovery: bool = True,
            confirmed: bool = False,
            max_recovery_attempts: int = 1) -> dict[str, Any]:
        # CognitiveBrain already performs bounded action/observation execution.
        # This wrapper adds an auditable adaptive summary and persists the
        # strategy state produced by the run.
        result = self.brain.run(request, session_id=session_id, max_steps=max_steps, inputs=inputs, research=research)
        history = result.get('history', [])
        meta = self.brain.meta.evaluate(history) if self.brain.meta else None
        prediction = self.brain.predictive_recovery.predict(request, history) if self.brain.predictive_recovery else None
        guidance = self.brain.meta.guidance(history) if self.brain.meta else None
        recovery_result = None
        if recovery and meta and meta.get('mode') == 'switch' and hasattr(self.brain.agent, 'recovery_execution'):
            last = history[-1] if history else {}
            failure = last.get('result') if isinstance(last, dict) else None
            diagnosis = last.get('diagnostic') if isinstance(last, dict) else None
            recovery_result = self.brain.agent.recovery_execution.run(
                request,
                failure=str(failure or meta.get('reason', 'falha repetida')),
                diagnosis=diagnosis if isinstance(diagnosis, dict) else {},
                session_id=session_id,
                confirmed=confirmed,
                max_attempts=max_recovery_attempts,
            )
        switches = 1 if meta and meta.get('mode') == 'switch' else 0
        self.data['strategy_switches'] = int(self.data.get('strategy_switches', 0)) + switches
        run = {
            'request': request,
            'session_id': session_id,
            'status': result.get('status'),
            'research_enabled': research,
            'steps': result.get('step', len(history)),
            'meta_reasoning': meta,
            'prediction': prediction,
            'guidance': guidance,
            'learned_strategies': self.brain.learning.suggest(request, 5) if self.brain.learning else [],
            'recovery': recovery_result,
        }
        self.data['runs'].append(run)
        self.data['runs'] = self.data['runs'][-100:]
        self._save()
        result['adaptive'] = run
        return result

    def status(self) -> dict[str, Any]:
        return {
            'ok': True,
            'runs': len(self.data.get('runs', [])),
            'strategy_switches': self.data.get('strategy_switches', 0),
            'path': str(self.path),
            'brain': self.brain.status(),
        }
