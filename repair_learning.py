from __future__ import annotations
import hashlib, json, re, time
from pathlib import Path
from typing import Any


class RepairLearning:
    """Persistent local knowledge base of failures, diagnoses and successful repairs.

    This is retrieval-based learning: it does not retrain a model. It stores structured
    repair cases and retrieves similar cases so a future engineering cycle can reuse them.
    """
    def __init__(self, root: str | Path, max_cases: int = 500):
        self.root = Path(root).resolve()
        self.path = self.root / '.aurora' / 'repair_learning.json'
        self.max_cases = max(1, int(max_cases))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return data if isinstance(data, dict) else {'cases': []}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {'cases': []}

    def _save(self, data: dict[str, Any]):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {x.lower() for x in re.findall(r'[\wÀ-ÿ]+', text or '') if len(x) > 2}

    @classmethod
    def _fingerprint(cls, failure: str, diagnosis: Any, target: str | None) -> str:
        payload = json.dumps({'failure': failure, 'diagnosis': diagnosis, 'target': target},
                             ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def record(self, failure: str, diagnosis: Any, repair: str = '', target: str | None = None,
               success: bool = False, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        data = self._load()
        case = {
            'id': hashlib.sha256(f'{time.time_ns()}:{failure}'.encode()).hexdigest()[:12],
            'fingerprint': self._fingerprint(failure, diagnosis, target),
            'failure': str(failure), 'diagnosis': diagnosis, 'repair': str(repair),
            'target': target, 'success': bool(success), 'metadata': metadata or {},
            'timestamp': time.time(),
        }
        cases = data.setdefault('cases', [])
        cases.append(case)
        data['cases'] = cases[-self.max_cases:]
        data['last'] = case
        self._save(data)
        return case

    def similar(self, failure: str, diagnosis: Any = None, target: str | None = None,
                limit: int = 5) -> list[dict[str, Any]]:
        query = self._terms(f'{failure} {json.dumps(diagnosis, ensure_ascii=False, default=str)} {target or ""}')
        scored = []
        for case in self._load().get('cases', []):
            hay = self._terms(f"{case.get('failure','')} {json.dumps(case.get('diagnosis',{}), ensure_ascii=False, default=str)} {case.get('target','')}")
            overlap = len(query & hay)
            if overlap:
                score = overlap + (2 if case.get('success') else 0)
                scored.append((score, case))
        scored.sort(key=lambda item: (item[0], item[1].get('timestamp', 0)), reverse=True)
        return [case for _, case in scored[:max(1, int(limit))]]


    @staticmethod
    def _normalize_pattern(text: str) -> str:
        text = str(text or '').lower()
        text = re.sub(r'[\"\']', '', text)
        text = re.sub(r'\b[0-9a-f]{8,}\b', '<id>', text)
        text = re.sub(r'\b\d+\b', '<n>', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:300]

    def patterns(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return reusable patterns distilled from successful repair cases."""
        groups: dict[str, dict[str, Any]] = {}
        for case in self._load().get('cases', []):
            if not case.get('success'):
                continue
            key = self._normalize_pattern(str(case.get('failure', '')))
            if not key:
                continue
            item = groups.setdefault(key, {
                'pattern': key, 'count': 0, 'successes': 0,
                'repairs': [], 'targets': [], 'last_timestamp': 0,
            })
            item['count'] += 1
            item['successes'] += 1
            if case.get('repair') and case['repair'] not in item['repairs']:
                item['repairs'].append(case['repair'])
            if case.get('target') and case['target'] not in item['targets']:
                item['targets'].append(case['target'])
            item['last_timestamp'] = max(item['last_timestamp'], case.get('timestamp', 0))
        values = list(groups.values())
        values.sort(key=lambda x: (x['count'], x['last_timestamp']), reverse=True)
        return values[:max(1, int(limit))]

    def contextual(self, failure: str, diagnosis: Any = None, target: str | None = None,
                   limit: int = 5) -> dict[str, Any]:
        """Build compact reusable repair context for an engineering attempt."""
        matches = self.similar(failure, diagnosis, target, limit=limit)
        patterns = self.patterns(limit=limit)
        return {
            'ok': True, 'query': {'failure': failure, 'target': target},
            'matches': matches, 'patterns': patterns,
            'guidance': [m.get('repair') for m in matches if m.get('success') and m.get('repair')],
        }

    def status(self) -> dict[str, Any]:
        data = self._load()
        cases = data.get('cases', [])
        return {'ok': True, 'cases': len(cases), 'successful_repairs': sum(bool(c.get('success')) for c in cases), 'last': data.get('last')}
