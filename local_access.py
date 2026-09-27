"""Local-first ownership/access for personal Aurora installations.

No account, password, OAuth or remote identity is required. The installation
itself is the owner boundary; state is persisted inside the workspace.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

class LocalAccess:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / '.aurora' / 'local_access.json'
        self.root.mkdir(parents=True, exist_ok=True)
        self._state = self._load_or_create()

    def _load_or_create(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding='utf-8'))
            except Exception:
                pass
        state = {
            'mode': 'local_owner',
            'login_required': False,
            'remote_identity_required': False,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        self.path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        return state

    def status(self):
        return dict(self._state, workspace=str(self.root))

    def authorize(self):
        """Return local authorization without requiring a login."""
        return {'authorized': True, 'mode': 'local_owner', 'login_required': False}
