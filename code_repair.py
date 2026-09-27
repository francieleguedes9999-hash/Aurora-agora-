from __future__ import annotations
import ast
import json
from pathlib import Path
from typing import Any


class CodeRepair:
    """Safe source repair using exact-content patches plus syntax validation."""
    def __init__(self, workspace, patcher):
        self.root = Path(workspace).resolve()
        self.patcher = patcher
        self.state_path = self.root / '.aurora' / 'code_repair.json'
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _path(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError('caminho fora do workspace')
        return p

    def inspect(self, path: str) -> dict[str, Any]:
        p = self._path(path)
        text = p.read_text(encoding='utf-8')
        result = {'ok': True, 'path': path, 'syntax_ok': True, 'error': None}
        if p.suffix == '.py':
            try:
                ast.parse(text, filename=str(p))
            except SyntaxError as exc:
                result.update(syntax_ok=False, error=str(exc))
        return result

    def repair(self, path: str, old: str, new: str, expected_sha256: str | None = None,
               validate=True) -> dict[str, Any]:
        p = self._path(path)
        current = p.read_text(encoding='utf-8') if p.exists() else ''
        if current != old:
            return {'ok': False, 'error': 'conteúdo atual não corresponde ao esperado', 'path': path}
        preview = self.patcher.preview(path, old, new)
        applied = self.patcher.apply(path, old, new, expected_sha256)
        validation = self.inspect(path) if validate else {'ok': True, 'syntax_ok': True}
        if not validation.get('syntax_ok', True):
            rollback = self.patcher.rollback_last()
            return {'ok': False, 'path': path, 'patch': applied, 'validation': validation,
                    'rolled_back': rollback}
        state = {'last': {'path': path, 'patch_id': applied.get('patch_id'), 'validation': validation}}
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        return {'ok': True, 'path': path, 'patch': applied, 'preview': preview, 'validation': validation}

    def plan_from_diagnosis(self, diagnosis: dict[str, Any] | None) -> dict[str, Any]:
        diagnosis = diagnosis or {}
        files = diagnosis.get('files') or diagnosis.get('affected_files') or []
        return {'ok': True, 'steps': [
            {'action': 'inspect', 'path': str(f)} for f in files if f
        ], 'requires_exact_patch': True}

    def status(self):
        try:
            return {'ok': True, 'exists': self.state_path.exists(),
                    'last': json.loads(self.state_path.read_text(encoding='utf-8'))}
        except Exception:
            return {'ok': True, 'exists': False, 'last': None}
