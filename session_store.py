from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class SessionMessage:
    role: str
    content: str
    created_at: str
    metadata: dict[str, Any]

class SessionStore:
    """Persistent conversation/session state stored locally inside the workspace."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.dir = self.root / '.aurora' / 'sessions'
        self.dir.mkdir(parents=True, exist_ok=True)

    def create(self, title: str = '') -> str:
        sid = uuid.uuid4().hex[:16]
        self._path(sid).write_text(json.dumps({
            'id': sid, 'title': title, 'created_at': _now(), 'updated_at': _now(),
            'messages': [], 'state': {}
        }, ensure_ascii=False, indent=2), encoding='utf-8')
        return sid

    def _path(self, session_id: str) -> Path:
        safe = ''.join(c for c in session_id if c.isalnum() or c in '-_')
        if not safe or safe != session_id:
            raise ValueError('session_id inválido')
        return self.dir / f'{safe}.json'

    def load(self, session_id: str) -> dict[str, Any]:
        try:
            return json.loads(self._path(session_id).read_text(encoding='utf-8'))
        except FileNotFoundError:
            raise KeyError(f'sessão não encontrada: {session_id}')

    def ensure(self, session_id: str | None = None, title: str = '') -> str:
        if session_id:
            try:
                self.load(session_id)
                return session_id
            except KeyError:
                self.create(title)
                # create generates a new id; callers should not silently get another id
                raise
        return self.create(title)

    def append(self, session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        data = self.load(session_id)
        data.setdefault('messages', []).append(asdict(SessionMessage(role, content, _now(), metadata or {})))
        data['updated_at'] = _now()
        self._path(session_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def set_state(self, session_id: str, **values: Any) -> dict[str, Any]:
        data = self.load(session_id)
        data.setdefault('state', {}).update(values)
        data['updated_at'] = _now()
        self._path(session_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return data['state']

    def recent(self, session_id: str, limit: int = 12) -> list[dict[str, Any]]:
        return self.load(session_id).get('messages', [])[-limit:]

    def list(self) -> list[dict[str, Any]]:
        out = []
        for p in sorted(self.dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                d = json.loads(p.read_text(encoding='utf-8'))
                out.append({k: d.get(k) for k in ('id','title','created_at','updated_at')})
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        return out
