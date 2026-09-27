from __future__ import annotations
import json
import copy
from pathlib import Path
from typing import Any


class PredictiveCognitiveRecovery:
    """Predicts risky tool choices from local cognitive history.

    This is deterministic evidence-based control, not model training. It uses
    prior failed/successful tool sequences to warn the model before execution
    and propose alternatives when a strategy has a known failure pattern.
    """
    def __init__(self, root, learning=None):
        self.root = Path(root)
        self.learning = learning
        self.path = self.root / '.aurora' / 'brain_predictive_recovery.json'
        self.data: dict[str, Any] = {'predictions': [], 'warnings': 0}
        self._load()

    def _load(self):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(value, dict):
                self.data.update(value)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    @staticmethod
    def _key(request: str) -> set[str]:
        return set(''.join(c.lower() if c.isalnum() or c.isspace() else ' ' for c in request).split())

    @staticmethod
    def _failed(item: dict[str, Any]) -> bool:
        result = item.get('result') if isinstance(item, dict) else None
        if not isinstance(result, dict):
            return bool(item.get('diagnostic')) if isinstance(item, dict) else False
        return result.get('ok') is False or result.get('passed') is False or result.get('returncode', 0) not in (0, None)

    def predict(self, request: str, history: list[dict[str, Any]] | None = None, limit: int = 5) -> dict[str, Any]:
        history = history or []
        words = self._key(request)
        recent = history[-8:]
        failed_tools = [h.get('action', {}).get('tool') for h in recent if self._failed(h) and h.get('action', {}).get('tool')]
        repeated = bool(failed_tools and len(failed_tools) >= 2 and failed_tools[-1] == failed_tools[-2])
        suggestions = self.learning.suggest(request, limit) if self.learning else []
        risky = list(dict.fromkeys(failed_tools))
        alternatives = []
        for strategy in suggestions:
            for tool in strategy.get('sequence', []):
                if tool not in risky and tool not in alternatives:
                    alternatives.append(tool)
        # Historical failed events provide stronger evidence than a single run.
        historical_failures = 0
        if self.learning:
            for event in self.learning.data.get('events', []):
                if event.get('success') is False and (not words or words & set(str(event.get('key', '')).split())):
                    historical_failures += 1
        if repeated:
            risk, reason = 'high', 'a última ferramenta falhou repetidamente nesta execução'
        elif failed_tools or historical_failures:
            risk, reason = 'medium', 'há evidência recente ou histórica de falha para estratégias semelhantes'
        else:
            risk, reason = 'low', 'não há evidência suficiente de risco nesta execução'
        prediction = {
            'risk': risk,
            'reason': reason,
            'risky_tools': risky[:limit],
            'alternative_tools': alternatives[:limit],
            'historical_failures': historical_failures,
            'repeated_failure': repeated,
        }
        self.data['predictions'].append(prediction)
        self.data['predictions'] = self.data['predictions'][-300:]
        if risk in {'medium', 'high'}:
            self.data['warnings'] = int(self.data.get('warnings', 0)) + 1
        self._save()
        return prediction

    def peek(self, request: str, history: list[dict[str, Any]] | None = None, limit: int = 5) -> dict[str, Any]:
        # Compute without persistence so prompt construction is side-effect free.
        old = self.data
        snapshot = copy.deepcopy(self.data)
        prediction = self.predict(request, history, limit)
        self.data = snapshot
        if old is not snapshot:
            pass
        return prediction

    def guidance(self, prediction: dict[str, Any]) -> str:
        if prediction.get('risk') == 'high':
            alternatives = ', '.join(prediction.get('alternative_tools', [])) or 'diagnose/inspect'
            return f"Risco alto: evite repetir {', '.join(prediction.get('risky_tools', [])) or 'a abordagem anterior'}. Prepare uma alternativa ({alternatives}) antes de executar."
        if prediction.get('risk') == 'medium':
            return 'Risco moderado: valide o contexto e prefira uma alternativa já observada como útil se ela produzir evidência verificável.'
        return 'Risco baixo: nenhuma mudança preventiva é necessária; mantenha a estratégia se os resultados forem verificáveis.'

    def status(self):
        return {'ok': True, 'predictions': len(self.data.get('predictions', [])), 'warnings': self.data.get('warnings', 0), 'path': str(self.path)}
