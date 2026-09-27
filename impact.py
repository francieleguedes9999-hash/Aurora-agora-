from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

class ImpactPlanner:
    """Uses the local knowledge graph to scope safe edits and targeted tests."""
    def __init__(self, root: str | Path, graph: Any):
        self.root = Path(root).resolve()
        self.graph = graph
        self.path = self.root / '.aurora' / 'impact.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _load(self) -> dict[str, Any]:
        try: return json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError): return {'history': []}

    def _tests_for(self, paths: set[str]) -> list[str]:
        tests = []
        all_tests = list((self.root / 'tests').rglob('test_*.py')) if (self.root/'tests').exists() else []
        names = {Path(p).stem.replace('test_', '') for p in paths}
        for p in all_tests:
            stem = p.stem[5:]
            if any(n in stem or stem in n for n in names) or not names:
                tests.append(str(p.relative_to(self.root)))
        return sorted(set(tests))[:50]

    def analyze(self, target: str, depth: int = 2, limit: int = 50, save: bool = True) -> dict[str, Any]:
        impact = self.graph.impact(target, depth=depth, limit=limit)
        paths = {n.get('path') for n in impact.get('nodes', []) if n.get('type') == 'file' and n.get('path')}
        direct = {target} if target in paths else set()
        tests = self._tests_for(paths)
        payload = {
            'ok': True, 'target': target, 'depth': depth,
            'files': sorted(paths), 'direct': sorted(direct),
            'tests': tests, 'graph_fingerprint': self.graph.status().get('fingerprint'),
            'count': len(paths),
        }
        payload['fingerprint'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        if save:
            state = self._load(); state.setdefault('history', []).append(payload); state['last'] = payload; self._save(state)
        return payload

    def preflight(self, target: str, depth: int = 2) -> dict[str, Any]:
        plan = self.analyze(target, depth=depth)
        return {'ok': True, 'target': target, 'files_to_review': plan['files'], 'tests_to_run': plan['tests'], 'fingerprint': plan['fingerprint']}

    def status(self) -> dict[str, Any]:
        state = self._load(); last = state.get('last')
        return {'ok': True, 'exists': bool(last), 'history': len(state.get('history', [])), 'last': last}
