from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from typing import Any, Callable

IGNORE_DIRS = {'.aurora', '.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv'}
TEXT_EXTS = {'.py','.js','.ts','.tsx','.jsx','.json','.md','.txt','.html','.css','.scss','.yaml','.yml','.toml','.sql'}


class ChangeIntelligence:
    """Compare planned impact with the files actually changed by an operation."""
    def __init__(self, root: str | Path, impact: Any, graph: Any | None = None):
        self.root = Path(root).resolve()
        self.impact = impact
        self.graph = graph
        self.path = self.root / '.aurora' / 'change_intelligence.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _files(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if not self.root.exists():
            return out
        for p in self.root.rglob('*'):
            if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
                continue
            try:
                rel = p.relative_to(self.root)
            except ValueError:
                continue
            if any(part in IGNORE_DIRS for part in rel.parts):
                continue
            try:
                out[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                pass
        return out

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {'history': []}

    def _save(self, state: dict[str, Any]) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def plan(self, target: str, depth: int = 2, limit: int = 50) -> dict[str, Any]:
        predicted = self.impact.analyze(target, depth=depth, limit=limit)
        files = sorted(set(predicted.get('files', [])))
        payload = {
            'ok': True, 'target': target, 'predicted_files': files,
            'predicted_tests': predicted.get('tests', []),
            'impact_fingerprint': predicted.get('fingerprint'),
            'planned_at': time.time(),
        }
        payload['fingerprint'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return payload

    def compare(self, before: dict[str, str], after: dict[str, str], planned: dict[str, Any]) -> dict[str, Any]:
        before_keys, after_keys = set(before), set(after)
        added = sorted(after_keys - before_keys)
        removed = sorted(before_keys - after_keys)
        modified = sorted(k for k in before_keys & after_keys if before[k] != after[k])
        actual = sorted(set(added + removed + modified))
        predicted = set(planned.get('predicted_files', []))
        actual_set = set(actual)
        unexpected = sorted(actual_set - predicted)
        untouched_predicted = sorted(predicted - actual_set)
        covered = sorted(actual_set & predicted)
        coverage = (len(covered) / len(actual_set)) if actual_set else 1.0
        result = {
            'ok': True,
            'target': planned.get('target'),
            'predicted_files': sorted(predicted),
            'actual_files': actual,
            'added': added, 'removed': removed, 'modified': modified,
            'covered': covered, 'unexpected': unexpected,
            'predicted_but_untouched': untouched_predicted,
            'coverage': round(coverage, 6),
            'drift': bool(unexpected),
            'planned_fingerprint': planned.get('fingerprint'),
            'timestamp': time.time(),
        }
        result['fingerprint'] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
        return result

    def execute(self, target: str, runner: Callable[[], Any], depth: int = 2, limit: int = 50) -> dict[str, Any]:
        planned = self.plan(target, depth, limit)
        before = self._files()
        started = time.time()
        try:
            result = runner()
            runner_error = None
        except Exception as exc:
            result = {'ok': False, 'error': str(exc)}
            runner_error = str(exc)
        after = self._files()
        comparison = self.compare(before, after, planned)
        record = {'ok': not runner_error and not (isinstance(result, dict) and result.get('ok') is False),
                  'target': target, 'result': result, 'plan': planned, 'comparison': comparison,
                  'duration_seconds': round(time.time() - started, 6)}
        state = self._load()
        state.setdefault('history', []).append(record)
        state['last'] = record
        self._save(state)
        return record

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {'ok': True, 'history': len(state.get('history', [])), 'last': state.get('last')}
