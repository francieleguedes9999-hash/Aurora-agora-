from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class BrainMemory:
    """Persistent cognitive-session state, separate from long-term user memory."""
    def __init__(self, root, max_sessions: int = 50):
        self.root = Path(root)
        self.path = self.root / '.aurora' / 'brain_sessions.json'
        self.max_sessions = max_sessions
        self.sessions: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            self.sessions = data if isinstance(data, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.sessions = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.sessions, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    def get(self, session_id: str) -> dict[str, Any]:
        return self.sessions.get(session_id, {'session_id': session_id, 'turns': [], 'facts': []})

    def record(self, session_id: str, request: str, result: Any, history: list[dict[str, Any]]):
        state = self.get(session_id)
        state['turns'].append({'request': request, 'result': result, 'history': history[-12:]})
        state['turns'] = state['turns'][-20:]
        self.sessions[session_id] = state
        if len(self.sessions) > self.max_sessions:
            for key in list(self.sessions)[:-self.max_sessions]:
                self.sessions.pop(key, None)
        self._save()

    def status(self):
        return {'ok': True, 'sessions': len(self.sessions), 'path': str(self.path)}
