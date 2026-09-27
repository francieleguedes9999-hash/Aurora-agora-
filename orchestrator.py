from __future__ import annotations
import hashlib, json, time, uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

@dataclass
class OrchestratorRun:
    id: str
    request: str
    status: str = 'running'
    phase: str = 'plan'
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    stages: list[dict[str, Any]] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

class AuroraOrchestrator:
    """High-level controller for Aurora's existing deterministic subsystems.

    It does not replace Studio or Release Intelligence. Instead it decides when
    to reuse a successful stage, when to resume, and when a fresh execution is
    required. State is persisted so interrupted runs can be resumed safely.
    """
    STAGES = ('studio', 'release_intelligence', 'complete')

    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'orchestrator.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return {'current': None, 'history': []}

    def _save(self, state):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    @staticmethod
    def _fingerprint(request: str, options: dict[str, Any]) -> str:
        raw = json.dumps({'request': request.strip(), 'options': options}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _ok(value: Any) -> bool:
        return bool(value) if not isinstance(value, dict) else bool(value.get('ok'))

    def status(self):
        state = self._load()
        return {'ok': True, 'current': state.get('current'), 'count': len(state.get('history', []))}

    def plan(self, request: str, deploy: bool = False, dry_run: bool = False, verify: bool = False):
        if not request or not request.strip():
            return {'ok': False, 'error': 'descrição vazia'}
        stages = ['studio']
        if deploy or verify:
            stages.append('release_intelligence')
        stages.append('complete')
        return {'ok': True, 'request': request.strip(), 'stages': stages,
                'reuse': ['studio', 'release_intelligence'], 'deploy': deploy,
                'dry_run': dry_run, 'verify': verify}

    def run(self, request: str, deploy: bool = False, dry_run: bool = False,
            verify: bool = False, label: str = 'orchestrated-release',
            deploy_config: dict | None = None, session_id: str | None = None,
            max_steps: int = 12, force: bool = False) -> dict[str, Any]:
        if not request or not request.strip():
            return {'ok': False, 'status': 'invalid_request', 'error': 'descrição vazia'}
        request = request.strip()
        options = {'deploy': bool(deploy), 'dry_run': bool(dry_run), 'verify': bool(verify), 'label': label,
                   'deploy_config': deploy_config or {}, 'session_id': session_id}
        fp = self._fingerprint(request, options)
        state = self._load()
        previous = state.get('current')
        run = OrchestratorRun(uuid.uuid4().hex[:12], request)
        run.outputs['fingerprint'] = fp
        state['current'] = asdict(run)
        self._save(state)

        # Reuse a completed identical run only when no deployment action is requested.
        if not force and not deploy and previous and previous.get('status') == 'completed' and previous.get('outputs', {}).get('fingerprint') == fp:
            run.status = 'completed'; run.phase = 'complete'; run.skipped = list(previous.get('stages', []))
            run.outputs['reused_run_id'] = previous.get('id')
            run.finished_at = time.time()
            return self._finish(state, run)

        studio = None
        if not force and previous and previous.get('status') in {'running', 'interrupted'} and previous.get('request') == request:
            # Ask Studio to resume its own persisted state instead of starting over.
            run.phase = 'studio'
            studio = self.agent._call('studio', {'action': 'resume', 'request': request,
                'session_id': session_id, 'max_steps': max_steps, 'deploy': False})
            run.skipped.append('orchestrator_resume')
        else:
            run.phase = 'studio'
            studio = self.agent._call('studio', {'action': 'run', 'request': request,
                'session_id': session_id, 'max_steps': max_steps, 'deploy': False})
        run.stages.append({'name': 'studio', 'ok': self._ok(studio), 'result': studio, 'ts': time.time()})
        run.outputs['studio'] = studio
        self._persist_current(state, run)
        if not self._ok(studio):
            return self._finish(state, run, 'failed', 'studio_failed')

        if deploy or verify:
            run.phase = 'release_intelligence'
            release = self.agent._call('release_intelligence', {
                'action': 'run', 'request': request, 'label': label,
                'deploy_config': deploy_config, 'deploy': deploy,
                'dry_run': dry_run, 'verify': verify, 'session_id': session_id,
                'max_steps': max_steps})
            run.stages.append({'name': 'release_intelligence', 'ok': self._ok(release), 'result': release, 'ts': time.time()})
            run.outputs['release'] = release
            self._persist_current(state, run)
            if not self._ok(release):
                return self._finish(state, run, 'failed', 'release_failed')

        run.phase = 'complete'
        return self._finish(state, run, 'completed', None)

    def resume(self, request: str | None = None, **kwargs):
        current = self._load().get('current')
        if not current and not request:
            return {'ok': False, 'status': 'no_orchestrator_run'}
        req = request or current.get('request')
        return self.run(req, **kwargs)

    def _persist_current(self, state, run):
        state['current'] = asdict(run)
        self._save(state)

    def _finish(self, state, run, status: str | None = None, reason: str | None = None):
        if status:
            run.status = status
        run.finished_at = time.time()
        if reason:
            run.errors.append(reason)
        state['current'] = asdict(run)
        state.setdefault('history', []).append(asdict(run))
        self._save(state)
        return {'ok': run.status == 'completed', 'status': run.status,
                'orchestrator_id': run.id, 'phase': run.phase,
                'stages': run.stages, 'skipped': run.skipped,
                'outputs': run.outputs, 'errors': run.errors}
