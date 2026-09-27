from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from typing import Any, Callable

class RegressionIntelligence:
    """Selects and executes tests most likely affected by a change."""
    def __init__(self, root: str | Path, change_intelligence: Any, test_runner: Any):
        self.root = Path(root).resolve()
        self.change_intelligence = change_intelligence
        self.test_runner = test_runner
        self.path = self.root / '.aurora' / 'regression_intelligence.json'
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
    def _unique(items):
        return sorted({str(x) for x in items if x})

    def select(self, planned: dict[str, Any], comparison: dict[str, Any] | None = None, limit: int = 50):
        comparison = comparison or {}
        candidates = []
        candidates.extend(planned.get('predicted_tests', []))
        candidates.extend(comparison.get('tests', []))
        # A changed Python test file should run itself even if impact matching was sparse.
        for path in comparison.get('actual_files', []):
            if path.startswith('tests/') and path.endswith('.py'):
                candidates.append(path)
        selected = self._unique(candidates)[:max(1, int(limit))]
        return {
            'ok': True,
            'tests': selected,
            'count': len(selected),
            'reason': 'impact_and_change_overlap',
            'fingerprint': hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest(),
        }

    def run_selected(self, tests: list[str], runner: Callable[[str], dict[str, Any]] | None = None):
        runner = runner or (lambda path: self.test_runner.run(f'python -m pytest -q {path}'))
        results = []
        started = time.time()
        for path in tests:
            result = runner(path)
            results.append({'test': path, 'ok': bool(result.get('ok') or result.get('passed')), 'result': result})
            if not results[-1]['ok']:
                # Stop at first regression so the correction loop gets a focused failure.
                break
        passed = all(item['ok'] for item in results) and len(results) == len(tests)
        return {
            'ok': passed,
            'passed': passed,
            'selected': tests,
            'executed': [x['test'] for x in results],
            'results': results,
            'duration_seconds': round(time.time() - started, 6),
        }

    def validate(self, planned: dict[str, Any], comparison: dict[str, Any] | None = None,
                 runner: Callable[[str], dict[str, Any]] | None = None, limit: int = 50):
        selected = self.select(planned, comparison, limit)
        execution = self.run_selected(selected['tests'], runner)
        record = {
            'ok': execution['ok'],
            'planned_fingerprint': planned.get('fingerprint'),
            'change_fingerprint': (comparison or {}).get('fingerprint'),
            'selection': selected,
            'execution': execution,
            'timestamp': time.time(),
        }
        state = self._load()
        state.setdefault('history', []).append(record)
        state['last'] = record
        self._save(state)
        return record

    def status(self):
        state = self._load()
        return {'ok': True, 'history': len(state.get('history', [])), 'last': state.get('last')}
