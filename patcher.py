from __future__ import annotations
import difflib
import hashlib
import json
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class PatchRecord:
    id: str
    path: str
    before_sha256: str
    after_sha256: str
    backup: str
    created_at: str

class PatchEngine:
    """Edição atômica baseada em conteúdo, com pré-condição, diff e rollback."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.meta = self.root / '.aurora' / 'patches'
        self.meta.mkdir(parents=True, exist_ok=True)
        self.state = self.meta / 'state.json'

    def _path(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError('caminho fora do workspace')
        return p

    def _load(self) -> dict[str, Any]:
        try: return json.loads(self.state.read_text(encoding='utf-8'))
        except (OSError, ValueError): return {'history': [], 'last': None}

    def _save(self, data: dict[str, Any]) -> None:
        self.state.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    def preview(self, path: str, old: str, new: str) -> dict[str, Any]:
        p = self._path(path)
        current = p.read_text(encoding='utf-8')
        if current != old:
            raise ValueError('conteúdo atual não corresponde ao conteúdo esperado; recarregue o arquivo')
        diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=path, tofile=path))
        return {'ok': True, 'path': path, 'before_sha256': _sha(old), 'after_sha256': _sha(new), 'diff': diff}

    def apply(self, path: str, old: str, new: str, expected_sha256: str | None = None) -> dict[str, Any]:
        p = self._path(path)
        current = p.read_text(encoding='utf-8') if p.exists() else ''
        if current != old:
            raise ValueError('conteúdo atual não corresponde ao conteúdo esperado')
        before_sha = _sha(current)
        if expected_sha256 and expected_sha256 != before_sha:
            raise ValueError('hash de pré-condição não corresponde ao arquivo atual')
        patch_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')
        backup = self.meta / f'{patch_id}.bak'
        backup.write_text(current, encoding='utf-8')
        tmp = p.with_name(p.name + '.aurora.tmp')
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(new, encoding='utf-8')
        tmp.replace(p)
        rec = PatchRecord(patch_id, str(p.relative_to(self.root)), before_sha, _sha(new), str(backup.relative_to(self.root)), _now())
        data = self._load(); data.setdefault('history', []).append(asdict(rec)); data['last'] = asdict(rec); self._save(data)
        return {'ok': True, 'patch_id': patch_id, 'path': rec.path, 'diff': ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=path, tofile=path))}

    def rollback_last(self) -> dict[str, Any]:
        data = self._load(); rec = data.get('last')
        if not rec: return {'ok': False, 'error': 'nenhuma edição para desfazer'}
        p = self._path(rec['path']); backup = self._path(rec['backup'])
        current = p.read_text(encoding='utf-8') if p.exists() else ''
        if _sha(current) != rec['after_sha256']:
            return {'ok': False, 'error': 'arquivo foi alterado depois da edição; rollback recusado'}
        shutil.copyfile(backup, p)
        data['last'] = None; self._save(data)
        return {'ok': True, 'rolled_back': rec['id'], 'path': rec['path']}
