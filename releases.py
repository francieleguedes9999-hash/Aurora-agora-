from __future__ import annotations
import json, time, uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .artifacts import ArtifactManager
from .deploy import DeployManager
from .versions import ProjectVersionManager

@dataclass
class ReleaseRecord:
    id: str
    number: int
    label: str
    version_id: str | None
    artifact_id: str | None
    deployment_id: str | None
    status: str
    created_at: float
    deployed_at: float | None = None
    verified_at: float | None = None

class ReleaseManager:
    """Coordinates project version, artifact and deployment into one release."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.dir = self.root / '.aurora' / 'releases'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.dir / 'state.json'
        self.versions = ProjectVersionManager(self.root)
        self.artifacts = ArtifactManager(self.root)
        self.deployments = DeployManager(self.root)

    def _load(self):
        try:
            return json.loads(self.state_path.read_text(encoding='utf-8'))
        except Exception:
            return {'current': None, 'history': []}

    def _save(self, state):
        tmp = self.state_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.state_path)

    def _record(self, rec: ReleaseRecord):
        state = self._load()
        state.setdefault('history', []).append(asdict(rec))
        state['current'] = asdict(rec)
        self._save(state)
        return asdict(rec)

    def status(self):
        state = self._load()
        return {'ok': True, 'current': state.get('current'), 'count': len(state.get('history', []))}

    def list(self):
        return {'ok': True, 'releases': self._load().get('history', [])}

    def history(self, limit=20):
        return {'ok': True, 'releases': self._load().get('history', [])[-max(1, int(limit)): ]}

    def _get(self, release_id):
        return next((x for x in self._load().get('history', []) if x['id'] == release_id), None)

    def plan(self, label='release', create_snapshot=True, build_artifact=True):
        steps=[]
        if create_snapshot: steps.append('snapshot')
        if build_artifact: steps.append('build_artifact')
        steps.append('register_release')
        return {'ok': True, 'label': label, 'steps': steps, 'workspace': str(self.root)}

    def create(self, label='release', snapshot=True, artifact=True):
        if not label or not label.strip():
            return {'ok': False, 'error': 'label vazio'}
        version_id = None
        artifact_id = None
        if snapshot:
            snap = self.versions.snapshot(label.strip())
            if not snap.get('ok'):
                return {'ok': False, 'stage': 'snapshot', 'result': snap}
            version_id = snap['version']['id']
        if artifact:
            built = self.artifacts.build(label.strip())
            if not built.get('ok'):
                return {'ok': False, 'stage': 'artifact', 'version_id': version_id, 'result': built}
            artifact_id = built['artifact']['id']
        state = self._load()
        number = len(state.get('history', [])) + 1
        rec = ReleaseRecord(
            id=f'rel-{number:04d}-{uuid.uuid4().hex[:8]}', number=number,
            label=label.strip(), version_id=version_id, artifact_id=artifact_id,
            deployment_id=None, status='created', created_at=time.time())
        return {'ok': True, 'release': self._record(rec)}

    def deploy(self, release_id: str | None, config: dict[str, Any], dry_run=False):
        state = self._load()
        rec = self._get(release_id) if release_id else state.get('current')
        if not rec: return {'ok': False, 'error': 'release não encontrada'}
        artifact_path = None
        if rec.get('artifact_id'):
            arts = self.artifacts.list().get('artifacts', [])
            ar = next((x for x in arts if x['id'] == rec['artifact_id']), None)
            if ar: artifact_path = ar.get('package')
        result = self.deployments.deploy(config, artifact_path, dry_run=dry_run)
        if not result.get('ok'): return {'ok': False, 'stage': 'deploy', 'release': rec, 'result': result}
        if not dry_run:
            rec['deployment_id'] = result.get('deployment_id')
            rec['status'] = 'deployed'
            rec['deployed_at'] = time.time()
            self._replace(rec)
        return {'ok': True, 'release': rec, 'deployment': result}

    def verify(self, release_id=None, config=None):
        state=self._load(); rec=self._get(release_id) if release_id else state.get('current')
        if not rec: return {'ok': False, 'error':'release não encontrada'}
        cfg=config or {}
        result=self.deployments.verify(cfg)
        if result.get('ok') and result.get('verified'):
            rec['status']='verified'; rec['verified_at']=time.time(); self._replace(rec)
        return {'ok': result.get('ok', False), 'release': rec, 'verification': result}

    def rollback(self, release_id=None, target_release_id=None, config=None):
        state=self._load(); current=self._get(release_id) if release_id else state.get('current')
        target=self._get(target_release_id) if target_release_id else None
        if not current: return {'ok': False, 'error':'release atual não encontrada'}
        # DeployManager rollback targets its previous deployment. If a specific
        # release is requested, validate that it has a deployment identity.
        if target_release_id and not target:
            return {'ok': False, 'error':'release alvo não encontrada'}
        result=self.deployments.rollback(config or {})
        if not result.get('ok'): return {'ok': False, 'stage':'rollback', 'result':result}
        current['status']='rolled_back'; self._replace(current)
        return {'ok': True, 'release': current, 'rollback': result, 'target_release': target}

    def _replace(self, rec):
        state=self._load(); history=state.get('history', [])
        for i,item in enumerate(history):
            if item.get('id') == rec.get('id'): history[i]=rec; break
        state['history']=history; state['current']=rec; self._save(state)
