from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any


class RegressionEngineeringCoordinator:
    """Connects targeted regression detection to the engineering correction loop."""
    def __init__(self, agent: Any, max_attempts: int = 3):
        self.agent = agent
        self.max_attempts = max(1, int(max_attempts))
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'regression_engineering.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self, data: dict[str, Any]):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def _ok(self, value: Any) -> bool:
        if isinstance(value, dict):
            if 'ok' in value: return bool(value['ok'])
            if 'passed' in value: return bool(value['passed'])
        return bool(value)

    def _record(self, report, stage, result):
        report['stages'].append({'stage': stage, 'ok': self._ok(result), 'result': result, 'ts': time.time()})
        self._save(report)
        return result

    def run(self, request: str, session_id: str | None = None, research: bool = False,
            max_steps: int | None = None, max_attempts: int | None = None,
            limit: int = 50) -> dict[str, Any]:
        request = (request or '').strip()
        if not request:
            return {'ok': False, 'status': 'invalid_request', 'error': 'descrição vazia'}
        attempts = max(1, int(max_attempts or self.max_attempts))
        report = {
            'id': uuid.uuid4().hex[:12], 'request': request, 'status': 'running',
            'started_at': time.time(), 'attempts': 0, 'stages': [], 'errors': []
        }
        self._save(report)
        last = None
        next_request = request
        for attempt in range(1, attempts + 1):
            report['attempts'] = attempt
            current_request = next_request
            planned = self.agent.change_intelligence.plan(current_request, depth=2, limit=limit)
            self._record(report, f'change_plan_{attempt}', planned)
            before = self.agent.change_intelligence._files()

            cycle = self.agent.cycle.run(current_request, session_id=session_id)
            last = cycle
            self._record(report, f'cycle_{attempt}', cycle)

            after = self.agent.change_intelligence._files()
            comparison = self.agent.change_intelligence.compare(before, after, planned)
            self._record(report, f'change_compare_{attempt}', comparison)

            regression = self.agent.regression_intelligence.validate(planned, comparison, limit=limit)
            self._record(report, f'regression_{attempt}', regression)

            if self._ok(regression):
                if attempt > 1:
                    repair_learning = getattr(self.agent, 'repair_learning', None)
                    learned = (repair_learning.record(
                        failure='regression', diagnosis=regression,
                        repair=request, target=None, success=True,
                        metadata={'attempt': attempt, 'request': current_request},
                    ) if repair_learning is not None else None)
                    self._record(report, f'learning_success_{attempt}', learned)
                graph = self.agent._call('knowledge_graph', {'action': 'build', 'force': True})
                self._record(report, f'graph_refresh_{attempt}', graph)
                report['status'] = 'completed'
                report['result'] = {'cycle': cycle, 'comparison': comparison, 'regression': regression, 'attempt': attempt}
                break

            diagnosis = self.agent._call('diagnose', {'result': regression})
            self._record(report, f'diagnosis_{attempt}', diagnosis)
            report['errors'].append(str(diagnosis.get('error') if isinstance(diagnosis, dict) else diagnosis))
            repair_learning = getattr(self.agent, 'repair_learning', None)
            learned = (repair_learning.similar(
                failure=request, diagnosis=diagnosis,
                target=diagnosis.get('file') if isinstance(diagnosis, dict) else None, limit=5
            ) if repair_learning is not None else [])
            self._record(report, f'learning_matches_{attempt}', {'ok': True, 'cases': learned})
            if repair_learning is not None:
                repair_learning.record(
                    failure=current_request, diagnosis=diagnosis, repair='',
                    target=diagnosis.get('file') if isinstance(diagnosis, dict) else None,
                    success=False, metadata={'attempt': attempt},
                )
            if attempt < attempts:
                target = diagnosis.get('file') if isinstance(diagnosis, dict) else None
                target = target or request
                repair_request = f'Corrigir a regressão causada por: {current_request}. Diagnóstico: {diagnosis}'
                next_request = repair_request
                context = self.agent._call('context_intelligence', {
                    'action': 'stage_packet', 'request': repair_request, 'stage': 'correction',
                    'session_id': session_id, 'research': research, 'reuse': False,
                })
                self._record(report, f'repair_context_{attempt}', context)
                impact = self.agent._call('impact', {'action': 'preflight', 'target': target, 'depth': 2})
                self._record(report, f'repair_impact_{attempt}', impact)
                self.agent.memory.remember(
                    f'Regression attempt {attempt} failed: {diagnosis}. Targeted tests will be rerun after correction.',
                    kind='diagnosis', tags=['engineering', 'regression', 'repair'],
                    metadata={'attempt': attempt, 'target': target},
                )
            else:
                report['status'] = 'failed'

        report['finished_at'] = time.time()
        report['result'] = report.get('result') or {'last': last, 'attempt': report['attempts']}
        self._save(report)
        return {'ok': report['status'] == 'completed', **report}

    def status(self):
        try:
            return {'ok': True, **json.loads(self.path.read_text(encoding='utf-8'))}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {'ok': True, 'status': 'none'}
