from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any


class ResearchExecution:
    """Executes a research-derived plan as small, verified engineering stages."""
    def __init__(self, agent: Any):
        self.agent = agent
        self.path = Path(agent.workspace.root) / '.aurora' / 'research_execution.json'
        self.data = {'runs': []}
        self._load()

    def _load(self):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(value, dict): self.data.update(value)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    @staticmethod
    def _ok(value: Any) -> bool:
        if not isinstance(value, dict): return bool(value)
        if 'ok' in value: return bool(value['ok'])
        if 'passed' in value: return bool(value['passed'])
        return True

    def run(self, request: str, session_id: str | None = None,
            max_stages: int = 5, max_retries: int = 1,
            research: bool = True, plan: dict[str, Any] | None = None) -> dict[str, Any]:
        request = (request or '').strip()
        if not request:
            return {'ok': False, 'status': 'invalid_request', 'error': 'descrição vazia'}
        if plan is None:
            plan = self.agent._call('research_plan', {'action': 'build', 'request': request, 'session_id': session_id})
        if not isinstance(plan, dict) or not plan.get('ok', True):
            return {'ok': False, 'status': 'planning_failed', 'plan': plan}
        steps = list(plan.get('steps') or [])[:max(1, int(max_stages))]
        run = {
            'id': uuid.uuid4().hex[:12], 'request': request, 'status': 'running',
            'started_at': time.time(), 'finished_at': None, 'plan': plan,
            'stages': [], 'session_id': session_id,
        }
        self.data['runs'].append(run); self.data['runs'] = self.data['runs'][-50:]; self._save()

        for step in steps:
            stage_id = step.get('id')
            stage = {'id': stage_id, 'stage': step.get('stage', 'implementation'),
                     'action': step.get('action', ''), 'attempts': [], 'status': 'running'}
            run['stages'].append(stage); self._save()
            stage_request = (
                f"Tarefa principal: {request}\n"
                f"Etapa {stage_id} ({step.get('stage', 'implementation')}): {step.get('action', '')}\n"
                "Execute somente esta etapa, preserve mudanças existentes e deixe um resultado verificável."
            )
            if step.get('evidence'):
                stage_request += f"\nOrientação baseada na pesquisa: {step['evidence']}"

            success = False
            for attempt in range(1, max(1, int(max_retries)) + 2):
                result = self.agent.cycle.run(stage_request, session_id=session_id)
                tests = self.agent._call('run_tests', {})
                entry = {'attempt': attempt, 'result': result, 'tests': tests, 'ok': self._ok(tests), 'ts': time.time()}
                stage['attempts'].append(entry); self._save()
                if self._ok(tests):
                    success = True; stage['status'] = 'completed'; break
                if attempt <= max_retries:
                    diagnosis = self.agent._call('diagnose', {'result': tests})
                    entry['diagnosis'] = diagnosis
                    repair = f"Corrija somente a falha desta etapa: {stage_request}\nDiagnóstico: {diagnosis}"
                    repair_result = self.agent.cycle.run(repair, session_id=session_id)
                    entry['repair'] = repair_result
                    self._save()
            if not success:
                stage['status'] = 'failed'
                run['status'] = 'failed'
                break

        if run['status'] == 'running': run['status'] = 'completed'
        run['finished_at'] = time.time(); self._save()
        return {'ok': run['status'] == 'completed', **run}

    def status(self):
        return {'ok': True, 'runs': len(self.data.get('runs', [])), 'path': str(self.path),
                'last': self.data.get('runs', [])[-1] if self.data.get('runs') else None}
