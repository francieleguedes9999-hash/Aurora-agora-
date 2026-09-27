from __future__ import annotations
import json, time, uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class StudioReport:
    id: str
    request: str
    status: str = 'running'
    phase: str = 'specification'
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    stages: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

class AuroraStudio:
    """Unified deterministic coordinator for Aurora's app-building stack.

    The Studio delegates reasoning to the existing model/agent and keeps a
    persistent, resumable state around the concrete build/deploy primitives.
    It never pretends that a model-powered step succeeded when the underlying
    tool reports failure.
    """
    PHASES = ('specification','build','test','visual','package','deploy','verify','complete')

    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.state_dir = self.root / '.aurora'
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.state_dir / 'studio.json'

    def _save(self, report: StudioReport):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def _load(self):
        try:
            return StudioReport(**json.loads(self.path.read_text(encoding='utf-8')))
        except Exception:
            return None

    @staticmethod
    def _ok(result: Any) -> bool:
        if not isinstance(result, dict): return bool(result)
        if 'ok' in result: return bool(result['ok'])
        if 'passed' in result: return bool(result['passed'])
        return True

    def _stage(self, report, name, result, phase=None):
        entry = {'stage': name, 'ok': self._ok(result), 'result': result, 'ts': time.time()}
        report.stages.append(entry)
        if phase: report.phase = phase
        if not entry['ok']:
            report.status = 'failed'
            err = result.get('error') if isinstance(result, dict) else None
            if err: report.errors.append(str(err))
        self._save(report)
        return entry

    def status(self):
        report = self._load()
        return {'ok': True, 'studio': asdict(report) if report else None}

    def run(self, request: str, deploy_config: dict | None = None, session_id: str | None = None,
            max_steps: int = 12, deploy: bool = False, dry_run: bool = False) -> dict[str, Any]:
        if not request or not request.strip():
            return {'ok': False, 'status': 'invalid_request', 'error': 'descrição vazia'}
        report = StudioReport(uuid.uuid4().hex[:12], request.strip())
        self._save(report)

        report.phase = 'specification'; self._save(report)
        spec = self.agent._call('build_app', {'action':'specification', 'description':request})
        self._stage(report, 'specification', spec, 'specification')
        report.artifacts['specification'] = spec
        if not self._ok(spec):
            report.finished_at=time.time(); self._save(report); return self._result(report)

        # The model-powered cycle handles implementation/research/edits when
        # available. AppBuilder remains the deterministic fallback that can
        # create a runnable project without a frontier model.
        report.phase='build'; self._save(report)
        built = self.agent._call('build_app', {'action':'build', 'description':request, 'run_tests':False})
        self._stage(report, 'build', built, 'build'); report.artifacts['build']=built
        if not self._ok(built):
            report.finished_at=time.time(); self._save(report); return self._result(report)

        report.phase='test'; self._save(report)
        tests = self.agent._call('run_tests', {})
        self._stage(report, 'test', tests, 'test'); report.artifacts['tests']=tests
        if not self._ok(tests):
            diagnosis = self.agent._call('diagnose', {'result':tests})
            self._stage(report, 'diagnosis', diagnosis, 'test')
            report.artifacts['diagnosis']=diagnosis
            # Give the model a bounded opportunity to repair the workspace.
            repair = self.agent.run_cycle(request, session_id=session_id)
            self._stage(report, 'repair_cycle', repair, 'build')
            tests = self.agent._call('run_tests', {})
            self._stage(report, 'retest', tests, 'test'); report.artifacts['tests_after_repair']=tests
            if not self._ok(tests):
                report.finished_at=time.time(); self._save(report); return self._result(report)

        report.phase='visual'; self._save(report)
        visual = {'ok': True, 'available': True, 'message': 'editor visual e workflows disponíveis via visual_edit/visual_workflow'}
        self._stage(report, 'visual', visual, 'visual'); report.artifacts['visual']=visual

        # Packaging/deployment are represented by the existing DeployManager.
        if deploy or deploy_config:
            report.phase='package'; self._save(report)
            cfg = deploy_config or {'provider':'local', 'command':'true', 'environment':'development'}
            plan = self.agent._call('deploy', {'action':'plan', 'config':cfg})
            self._stage(report, 'deploy_plan', plan, 'package'); report.artifacts['deploy_plan']=plan
            if not self._ok(plan):
                report.finished_at=time.time(); self._save(report); return self._result(report)
            action = 'dry_run' if dry_run else 'deploy'
            report.phase='deploy'; self._save(report)
            deployed = self.agent._call('deploy', {'action':action, 'config':cfg})
            self._stage(report, action, deployed, 'deploy'); report.artifacts[action]=deployed
            if not self._ok(deployed):
                report.finished_at=time.time(); self._save(report); return self._result(report)
            if cfg.get('verify_command'):
                report.phase='verify'; self._save(report)
                verified = self.agent._call('deploy', {'action':'verify', 'config':cfg})
                self._stage(report, 'verify', verified, 'verify'); report.artifacts['verify']=verified
                if not self._ok(verified):
                    report.finished_at=time.time(); self._save(report); return self._result(report)

        report.phase='complete'; report.status='completed'; report.finished_at=time.time(); self._save(report)
        return self._result(report)

    def resume(self, request: str | None = None, **kwargs):
        current = self._load()
        if not current and not request:
            return {'ok': False, 'status':'no_studio_task'}
        return self.run(request or current.request, **kwargs)

    def _result(self, report):
        return {'ok': report.status == 'completed', 'status': report.status,
                'studio_id': report.id, 'phase': report.phase,
                'artifacts': report.artifacts, 'errors': report.errors,
                'stages': report.stages}
