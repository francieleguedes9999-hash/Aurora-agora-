from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from typing import Any


class PredictiveEngineering:
    """Predict likely failure points before an engineering change.

    Uses local graph/impact information and successful repair history. This is
    heuristic prediction, not a claim that a failure will occur.
    """
    def __init__(self, root: str | Path, impact: Any, graph: Any, repair_learning: Any):
        self.root = Path(root).resolve()
        self.impact = impact
        self.graph = graph
        self.repair_learning = repair_learning
        self.path = self.root / '.aurora' / 'predictive_engineering.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {'history': []}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {'history': []}

    def _save(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    @staticmethod
    def _risk(score: int) -> str:
        if score >= 5:
            return 'high'
        if score >= 4:
            return 'medium'
        return 'low'

    def predict(self, target: str, depth: int = 2, limit: int = 50) -> dict[str, Any]:
        impact = self.impact.analyze(target, depth=depth, limit=limit)
        files = list(impact.get('files', []))
        tests = list(impact.get('tests', []))
        cases = self.repair_learning.similar(target, target=target, limit=8)
        successful = [c for c in cases if c.get('success')]

        predictions = []
        for path in files:
            score = 1
            reasons = ['arquivo está no impacto previsto']
            if path in files[:3]:
                score += 1
                reasons.append('arquivo aparece entre os primeiros itens do impacto')
            if path.startswith('tests/'):
                score += 1
                reasons.append('arquivo é teste e pode revelar regressão')
            if any(path == c.get('target') or path in str(c.get('target', '')) for c in successful):
                score += 3
                reasons.append('há histórico de reparo bem-sucedido relacionado')
            predictions.append({'file': path, 'risk_score': score,
                                'risk': self._risk(score), 'reasons': reasons})

        predictions.sort(key=lambda x: (-x['risk_score'], x['file']))
        preventive_tests = sorted(set(tests))
        high = [p for p in predictions if p['risk'] == 'high']
        payload = {
            'ok': True, 'target': target, 'depth': depth,
            'predictions': predictions, 'preventive_tests': preventive_tests,
            'related_repairs': successful[:8],
            'high_risk_count': len(high),
            'impact_fingerprint': impact.get('fingerprint'),
            'timestamp': time.time(),
        }
        payload['fingerprint'] = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        state = self._load()
        state.setdefault('history', []).append(payload)
        state['last'] = payload
        state['history'] = state['history'][-100:]
        self._save(state)
        return payload

    def preflight(self, target: str, depth: int = 2, limit: int = 50) -> dict[str, Any]:
        result = self.predict(target, depth, limit)
        return {
            'ok': True, 'target': target,
            'risk': 'high' if result['high_risk_count'] else ('medium' if result['predictions'] else 'low'),
            'files_to_review': [p['file'] for p in result['predictions']],
            'preventive_tests': result['preventive_tests'],
            'predictions': result['predictions'],
            'fingerprint': result['fingerprint'],
        }

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {'ok': True, 'history': len(state.get('history', [])), 'last': state.get('last')}
