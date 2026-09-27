from __future__ import annotations
import json, hashlib, time, uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class EngineeringReport:
    id: str
    request: str
    status: str = 'running'
    phase: str = 'context'
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    context: dict[str, Any] = field(default_factory=dict)
    impact: dict[str, Any] = field(default_factory=dict)
    stages: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)

class AutonomousEngineering:
    """Active engineering loop: context -> impact -> cycle -> tests -> graph.

    This coordinator is deterministic infrastructure. Model reasoning still
    comes from the configured Agent model; the coordinator only gates and
    records the engineering process.
    """
    def __init__(self, agent: Any, max_attempts: int = 3):
        self.agent = agent
        self.max_attempts = max(1, int(max_attempts))
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'engineering.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self, report: EngineeringReport):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    @staticmethod
    def _ok(value: Any) -> bool:
        if not isinstance(value, dict): return bool(value)
        if 'ok' in value: return bool(value['ok'])
        if 'passed' in value: return bool(value['passed'])
        return True

    def _stage(self, report, name, result, phase):
        entry = {'stage': name, 'phase': phase, 'ok': self._ok(result), 'result': result, 'ts': time.time()}
        report.stages.append(entry)
        report.phase = phase
        if not entry['ok']:
            err = result.get('error') if isinstance(result, dict) else None
            if err: report.errors.append(str(err))
        self._save(report)
        return entry

    def _target(self, request: str, impact: dict[str, Any]) -> str:
        files = impact.get('files') or []
        if files: return files[0]
        # No known target is acceptable; the agent can discover files itself.
        return request[:160]

    def run(self, request: str, session_id: str | None = None, research: bool = False,
            max_steps: int | None = None, max_attempts: int | None = None) -> dict[str, Any]:
        if not request or not request.strip():
            return {'ok': False, 'status': 'invalid_request', 'error': 'descrição vazia'}
        report = EngineeringReport(uuid.uuid4().hex[:12], request.strip())
        self._save(report)
        attempts = max(1, int(max_attempts or self.max_attempts))
        steps = max_steps or getattr(self.agent, 'max_steps', 12)

        context = self.agent._call('context_intelligence', {
            'action': 'stage_packet', 'request': request, 'stage': 'planning',
            'session_id': session_id, 'research': research, 'reuse': True,
        })
        self._stage(report, 'context', context, 'context')
        report.context = context if isinstance(context, dict) else {'value': context}

        # Build/reuse the graph before impact analysis. This makes the graph
        # an active input to engineering instead of a passive query database.
        graph = self.agent._call('knowledge_graph', {'action': 'build', 'force': False})
        self._stage(report, 'knowledge_graph', graph, 'context')
        impact = self.agent._call('impact', {'action': 'analyze', 'target': request, 'depth': 2, 'limit': 50})
        self._stage(report, 'impact', impact, 'impact')
        report.impact = impact if isinstance(impact, dict) else {'value': impact}

        plan = self.agent._call('plan', {'request': request, 'steps': []})
        self._stage(report, 'plan', plan, 'planning')

        last = None
        for attempt in range(1, attempts + 1):
            result = self.agent.cycle.run(request, session_id=session_id)
            last = result
            self._stage(report, f'cycle_{attempt}', result, 'implementation')
            tests = self.agent._call('run_tests', {})
            self._stage(report, f'tests_{attempt}', tests, 'testing')
            if self._ok(tests):
                # Refresh graph only after a successful state so its fingerprint
                # describes the workspace that actually passed the gate.
                rebuilt = self.agent._call('knowledge_graph', {'action': 'build', 'force': True})
                self._stage(report, 'graph_refresh', rebuilt, 'verification')
                report.status = 'completed'
                report.result = {'cycle': result, 'tests': tests, 'attempt': attempt}
                break
            diagnosis = self.agent._call('diagnose', {'result': tests})
            self._stage(report, f'diagnosis_{attempt}', diagnosis, 'diagnosis')
            report.result = {'cycle': result, 'tests': tests, 'diagnosis': diagnosis, 'attempt': attempt}
            if attempt < attempts:
                repair_request = f"Corrigir a falha detectada na tarefa: {request}. Diagnóstico: {diagnosis}"
                repair_context = self.agent._call('context_intelligence', {
                    'action': 'stage_packet', 'request': repair_request, 'stage': 'correction',
                    'session_id': session_id, 'research': research, 'reuse': False,
                })
                self._stage(report, f'repair_context_{attempt}', repair_context, 'correction')
                target = diagnosis.get('file') if isinstance(diagnosis, dict) else None
                target = target or request
                repair_impact = self.agent._call('impact', {'action': 'preflight', 'target': target, 'depth': 2})
                self._stage(report, f'repair_impact_{attempt}', repair_impact, 'correction')
                self.agent.memory.remember(
                    f'Engineering attempt {attempt} failed: {diagnosis}. Repair context and impact prepared for the next attempt.',
                    kind='diagnosis', tags=['engineering', 'repair', 'impact'],
                    metadata={'attempt': attempt, 'target': target},
                )
            else:
                report.status = 'failed'

        report.finished_at = time.time()
        self._save(report)
        return self._result(report)

    def resume(self, request: str | None = None, **kwargs):
        state = self.status()
        req = request or state.get('request')
        if not req: return {'ok': False, 'status': 'no_engineering_task'}
        return self.run(req, **kwargs)

    def status(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return {'ok': True, **data}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {'ok': True, 'status': 'none'}

    def fingerprint(self, request: str) -> str:
        return hashlib.sha256(request.strip().encode('utf-8')).hexdigest()

    def _result(self, report):
        return {'ok': report.status == 'completed', 'status': report.status,
                'engineering_id': report.id, 'phase': report.phase,
                'context': report.context, 'impact': report.impact,
                'result': report.result, 'errors': report.errors,
                'stages': report.stages}
