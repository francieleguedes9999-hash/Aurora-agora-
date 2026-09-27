from __future__ import annotations
import json
from pathlib import Path
from typing import Any


class BrainToolLearning:
    """Learns reusable tool-use strategies from observed cognitive runs.

    This is retrieval/statistical memory, not model training. Strategies are
    only promoted when their recorded outcomes are successful.
    """
    def __init__(self, root, max_strategies: int = 200):
        self.root = Path(root)
        self.path = self.root / '.aurora' / 'brain_tool_learning.json'
        self.max_strategies = max_strategies
        self.data: dict[str, Any] = {'strategies': [], 'events': []}
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
    def _key(request: str) -> str:
        words = ''.join(ch.lower() if ch.isalnum() or ch.isspace() else ' ' for ch in request).split()
        return ' '.join(words[:12])

    @staticmethod
    def _success(result: Any) -> bool:
        if not isinstance(result, dict):
            return True
        if result.get('ok') is False or result.get('passed') is False:
            return False
        return True

    def observe(self, request: str, history: list[dict[str, Any]], success: bool):
        sequence = [h.get('action', {}).get('tool') for h in history if h.get('action', {}).get('tool')]
        if not sequence:
            return
        event = {'key': self._key(request), 'sequence': sequence[-12:], 'success': bool(success)}
        self.data['events'].append(event)
        self.data['events'] = self.data['events'][-500:]
        if success:
            key = event['key']
            existing = next((s for s in self.data['strategies'] if s['key'] == key and s['sequence'] == event['sequence']), None)
            if existing:
                existing['successes'] += 1
                existing['last_used'] = len(self.data['events'])
            else:
                self.data['strategies'].append({'key': key, 'sequence': event['sequence'], 'successes': 1, 'last_used': len(self.data['events'])})
            self.data['strategies'] = sorted(self.data['strategies'], key=lambda s: (s['successes'], s['last_used']), reverse=True)[:self.max_strategies]
        self._save()

    def suggest(self, request: str, limit: int = 5) -> list[dict[str, Any]]:
        key_words = set(self._key(request).split())
        candidates = []
        for strategy in self.data.get('strategies', []):
            score = len(key_words & set(strategy.get('key', '').split()))
            if score:
                candidates.append((score, strategy.get('successes', 0), strategy))
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [dict(item[2], relevance=item[0]) for item in candidates[:limit]]

    def status(self):
        return {'ok': True, 'strategies': len(self.data.get('strategies', [])), 'events': len(self.data.get('events', [])), 'path': str(self.path)}
