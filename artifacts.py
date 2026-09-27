from __future__ import annotations
import hashlib, json, os, shutil, time, zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

@dataclass
class ArtifactRecord:
    id: str
    version: int
    package: str
    manifest: str
    sha256: str
    file_count: int
    created_at: float

class ArtifactManager:
    """Reproducible build/package manager with persistent artifact history."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.state_dir = self.root / '.aurora'
        self.artifacts_dir = self.state_dir / 'artifacts'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / 'artifacts.json'

    def _load(self):
        if not self.state_path.exists():
            return {'current': None, 'history': []}
        try: return json.loads(self.state_path.read_text(encoding='utf-8'))
        except Exception: return {'current': None, 'history': []}

    def _save(self, state):
        tmp = self.state_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.state_path)

    def _iter_files(self, exclude=None):
        exclude = set(exclude or ()) | {'.aurora', '__pycache__', '.pytest_cache', '.git'}
        for p in sorted(self.root.rglob('*')):
            if not p.is_file(): continue
            rel = p.relative_to(self.root)
            if any(part in exclude for part in rel.parts): continue
            yield p, rel.as_posix()

    @staticmethod
    def _sha(path):
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
        return h.hexdigest()

    def manifest(self, exclude=None):
        files=[]
        for p, rel in self._iter_files(exclude):
            files.append({'path': rel, 'size': p.stat().st_size, 'sha256': self._sha(p)})
        return {'format': 'aurora-manifest-v1', 'generated_from': str(self.root), 'files': files}

    def validate(self):
        errors=[]
        if not self.root.exists(): errors.append('workspace inexistente')
        if not self.root.is_dir(): errors.append('workspace não é diretório')
        return {'ok': not errors, 'errors': errors, 'file_count': len(list(self._iter_files())) if not errors else 0}

    def build(self, label='build', include_manifest=True):
        validation=self.validate()
        if not validation['ok']: return validation
        state=self._load(); version=len(state.get('history', []))+1
        aid=f'art-{version:04d}'
        out=self.artifacts_dir / f'{aid}-{label}.zip'
        manifest=self.manifest()
        manifest_path=self.artifacts_dir / f'{aid}-manifest.json'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        entries=list(self._iter_files())
        if include_manifest:
            entries.append((manifest_path, f'.aurora-manifest/{aid}.json'))
        with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p, rel in sorted(entries, key=lambda x:x[1]):
                info=zipfile.ZipInfo(rel, date_time=(2020,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=(p.stat().st_mode & 0o777) << 16
                with open(p,'rb') as f: z.writestr(info, f.read())
        record=ArtifactRecord(aid, version, str(out), str(manifest_path), self._sha(out), len(manifest['files']), time.time())
        state['current']=asdict(record); state.setdefault('history', []).append(asdict(record)); self._save(state)
        return {'ok': True, 'artifact': asdict(record), 'manifest': manifest}

    def list(self): return {'ok': True, 'artifacts': self._load().get('history', [])}
    def status(self): return {'ok': True, 'current': self._load().get('current'), 'count': len(self._load().get('history', []))}

    def verify(self, artifact_id=None):
        state=self._load(); rec=state.get('current') if not artifact_id else next((x for x in state.get('history',[]) if x['id']==artifact_id), None)
        if not rec: return {'ok': False, 'error':'artefato não encontrado'}
        p=Path(rec['package']); exists=p.exists(); digest=self._sha(p) if exists else None
        return {'ok': exists and digest==rec['sha256'], 'exists': exists, 'expected_sha256': rec['sha256'], 'sha256': digest, 'artifact': rec}

    def restore(self, artifact_id, destination=None):
        state=self._load(); rec=next((x for x in state.get('history',[]) if x['id']==artifact_id), None)
        if not rec: return {'ok': False, 'error':'artefato não encontrado'}
        import tempfile
        dest=Path(destination).resolve() if destination else (self.root / '.aurora' / 'restored' / artifact_id).resolve()
        if dest == self.root or self.root in dest.parents:
            if dest == self.root: return {'ok':False,'error':'destino não pode ser o workspace raiz'}
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(rec['package']) as z:
            for member in z.infolist():
                if member.filename.startswith('.aurora-manifest/'): continue
                target=(dest / member.filename).resolve()
                if dest != target and dest not in target.parents: return {'ok':False,'error':'path traversal detectado'}
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as src, open(target,'wb') as out: shutil.copyfileobj(src,out)
        return {'ok': True, 'artifact_id': artifact_id, 'destination': str(dest)}
