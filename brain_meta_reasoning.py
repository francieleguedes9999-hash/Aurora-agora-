from __future__ import annotations
import json
from pathlib import Path
from typing import Any


class MetaReasoning:
    """Deterministic strategy evaluator for the cognitive brain.

    It does not replace model reasoning. It measures recent tool outcomes and
    gives the model explicit signals about whether to persist, retry, or change
    strategy. State is persisted locally for auditability.
    """
    def __init__(self, root, max_history: int = 300):
        self.root = Path(root)
        self.path = self.root / '.aurora' / 'brain_meta_reasoning.json'
        self.max_history = max_history
        self.data: dict[str, Any] = {'evaluations': [], 'strategy_switches': 0}
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
    def _failed(result: Any) -> bool:
        if not isinstance(result, dict):
            return False
        return result.get('ok') is False or result.get('passed') is False or result.get('returncode', 0) not in (0, None)

    def evaluate(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        recent = history[-6:]
        tools = [h.get('action', {}).get('tool') for h in recent if h.get('action', {}).get('tool')]
        failures = [h for h in recent if self._failed(h.get('result')) or h.get('diagnostic')]
        last_tool = tools[-1] if tools else None
        repeated = bool(last_tool and len(tools) >= 2 and tools[-1] == tools[-2])
        same_tool_failures = sum(1 for h in recent if h.get('action', {}).get('tool') == last_tool and self._failed(h.get('result')))
        if not history:
            mode, confidence, reason = 'explore', 0.0, 'nenhuma evidência de execução ainda'
        elif failures and (repeated or same_tool_failures >= 2):
            mode, confidence, reason = 'switch', min(1.0, 0.55 + 0.15 * same_tool_failures), 'a estratégia recente apresentou falhas repetidas'
        elif failures:
            mode, confidence, reason = 'recover', 0.65, 'há uma falha recente; diagnosticar antes de repetir'
        else:
            mode, confidence, reason = 'continue', 0.8, 'a estratégia recente não apresentou falha observada'
        result = {'mode': mode, 'confidence': round(confidence, 3), 'reason': reason, 'last_tool': last_tool, 'recent_failures': len(failures), 'repeated_last_tool': repeated}
        self.data['evaluations'].append(result)
        self.data['evaluations'] = self.data['evaluations'][-self.max_history:]
        if mode == 'switch':
            self.data['strategy_switches'] = int(self.data.get('strategy_switches', 0)) + 1
        self._save()
        return result

    def peek(self, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate current evidence without persisting a duplicate event."""
        recent = history[-6:]
        tools = [h.get('action', {}).get('tool') for h in recent if h.get('action', {}).get('tool')]
        failures = [h for h in recent if self._failed(h.get('result')) or h.get('diagnostic')]
        last_tool = tools[-1] if tools else None
        repeated = bool(last_tool and len(tools) >= 2 and tools[-1] == tools[-2])
        same_tool_failures = sum(1 for h in recent if h.get('action', {}).get('tool') == last_tool and self._failed(h.get('result')))
        if not history:
            mode, confidence, reason = 'explore', 0.0, 'nenhuma evidência de execução ainda'
        elif failures and (repeated or same_tool_failures >= 2):
            mode, confidence, reason = 'switch', min(1.0, 0.55 + 0.15 * same_tool_failures), 'a estratégia recente apresentou falhas repetidas'
        elif failures:
            mode, confidence, reason = 'recover', 0.65, 'há uma falha recente; diagnosticar antes de repetir'
        else:
            mode, confidence, reason = 'continue', 0.8, 'a estratégia recente não apresentou falha observada'
        return {'mode': mode, 'confidence': round(confidence, 3), 'reason': reason, 'last_tool': last_tool, 'recent_failures': len(failures), 'repeated_last_tool': repeated}

    def guidance(self, history: list[dict[str, Any]]) -> str:
        state = self.peek(history)
        if state['mode'] == 'switch':
            return 'Mude de estratégia: não repita a mesma ferramenta/abordagem que acabou de falhar; use diagnóstico, contexto ou uma ferramenta alternativa.'
        if state['mode'] == 'recover':
            return 'Recupere primeiro: examine o resultado/diagnóstico antes de repetir a ação.'
        if state['mode'] == 'continue':
            return 'Continue a estratégia atual se ela estiver produzindo evidências úteis; não faça mudanças desnecessárias.'
        return 'Explore uma primeira ação que produza informação útil e verificável.'

    def status(self):
        return {'ok': True, 'evaluations': len(self.data.get('evaluations', [])), 'strategy_switches': self.data.get('strategy_switches', 0), 'path': str(self.path)}
