from __future__ import annotations
import json, time, uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .task_manager import TaskManager, Task
from .scheduler import ParallelScheduler


class ProjectOrchestrator:
    """Coordinates a project blueprint into dependency-aware engineering work.

    It keeps planning separate from execution and uses conservative resource
    locking: implementation tasks are serialized unless explicitly marked
    ``parallel_safe`` by the blueprint/task payload.
    """
    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'project_orchestrator.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.orchestration_root = self.root / '.aurora' / 'orchestrator'
        self.tasks = TaskManager(self.orchestration_root, max_workers=4)
        self.scheduler = ParallelScheduler(self.orchestration_root, tasks=self.tasks, max_workers=4)

    def _save(self, state: dict[str, Any]) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def _load(self) -> dict[str, Any] | None:
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def prepare(self, request: str, research: bool = True) -> dict[str, Any]:
        blueprint_result = self.agent.project_blueprint.build(request, research)
        if not blueprint_result.get('ok'):
            return blueprint_result
        blueprint = blueprint_result['blueprint']
        prefix = 'bp-' + blueprint['id'] + '-'
        existing = {t.id for t in self.tasks.tasks.values()}
        created = []
        id_map = {}
        for item in blueprint['tasks']:
            id_map[item['id']] = prefix + item['id']
        for item in blueprint['tasks']:
            tid = id_map[item['id']]
            if tid in existing:
                continue
            deps = [id_map[d] for d in item.get('depends_on', []) if d in id_map]
            # Workspace-changing work is locked by default. A future blueprint
            # can opt a task into safe parallelism explicitly.
            parallel_safe = bool(item.get('parallel_safe', False))
            resources = [] if parallel_safe else ['workspace']
            task = self.tasks.create(
                item['title'], kind='engineering',
                payload={
                    'blueprint_id': blueprint['id'],
                    'blueprint_task_id': item['id'],
                    'stage': item.get('stage', 'implementation'),
                    'context_query': item.get('context', ''),
                    'acceptance': item.get('acceptance', []),
                    'parallel_safe': parallel_safe,
                    'resources': resources,
                }, depends_on=deps, task_id=tid)
            created.append(asdict(task))
        evolution = self.agent.app_evolution.prepare(blueprint.get('spec', {}), blueprint.get('id', ''))
        if evolution.get('ok'):
            evolution_ids = []
            for module in evolution['state']['modules']:
                tid = prefix + module['id']
                if tid in existing:
                    continue
                task = self.tasks.create(
                    module['title'], kind='engineering',
                    payload={
                        'blueprint_id': blueprint['id'], 'blueprint_task_id': module['id'],
                        'stage': 'module_evolution', 'module_id': module['id'],
                        'parallel_safe': False, 'resources': ['workspace'],
                    }, depends_on=[id_map['bp_build_app']], task_id=tid)
                created.append(asdict(task)); evolution_ids.append(tid)
        all_task_ids = [id_map[x['id']] for x in blueprint['tasks']]
        if evolution.get('ok'):
            all_task_ids.extend(prefix + m['id'] for m in evolution['state']['modules'])
        state = {
            'id': uuid.uuid4().hex[:12], 'blueprint_id': blueprint['id'],
            'request': request.strip(), 'status': 'ready', 'created_at': time.time(),
            'task_ids': all_task_ids,
        }
        self._save(state)
        return {'ok': True, 'state': state, 'blueprint': blueprint, 'created_tasks': created}

    def _runner(self, task: Task) -> dict[str, Any]:
        payload = task.payload
        stage = payload.get('stage', 'implementation')
        blueprint_id = payload.get('blueprint_id')
        blueprint = self.agent.project_blueprint.load() or {}
        request = blueprint.get('request') or task.title

        # The build gate is the first real bridge between planning and artifact
        # creation. It uses the detailed contract already produced by the
        # blueprint/specification layer and creates the executable app.
        if stage == 'build':
            result = self.agent.app_builder.build(request, run_tests=False)
            if isinstance(result, dict):
                result['orchestration_stage'] = 'build'
                result['blueprint_id'] = blueprint_id
            return result

        if stage == 'module_evolution':
            module_id = payload.get('module_id', '')
            prompt = self.agent.app_evolution.prompt(module_id)
            if not prompt.get('ok'):
                return prompt
            self.agent.app_evolution.mark(module_id, 'running')
            attempts = max(1, min(3, int(payload.get('max_module_attempts', 2))))
            history = []
            last_result = None
            for attempt in range(1, attempts + 1):
                request = prompt['prompt']
                if history and not history[-1].get('validation', {}).get('ok'):
                    request += "\n\nCorrija especificamente os problemas encontrados na validação anterior:\n" + json.dumps(history[-1]['validation'], ensure_ascii=False, indent=2)
                result = self.agent.engineering.run(
                    request, research=False,
                    max_steps=getattr(self.agent, 'max_steps', 12), max_attempts=2,
                )
                validation = self.agent.app_evolution.validate(module_id)
                entry = {'attempt': attempt, 'engineering': result, 'validation': validation}
                history.append(entry)
                last_result = entry
                if result.get('ok') and validation.get('ok'):
                    final = {'ok': True, 'module_id': module_id, 'attempt': attempt, 'history': history}
                    self.agent.app_evolution.mark(module_id, 'done', final)
                    return final
                if not validation.get('ok'):
                    diagnosis = self.agent._call('diagnose', {'result': next((c for c in validation.get('checks', []) if not c.get('passed')), validation)})
                    entry['diagnosis'] = diagnosis
            final = {'ok': False, 'module_id': module_id, 'attempt': len(history), 'history': history, 'last_result': last_result}
            self.agent.app_evolution.mark(module_id, 'failed', final)
            return final

        acceptance = payload.get('acceptance') or []
        task_request = task.title
        if acceptance:
            task_request += '\nCritérios de aceitação:\n- ' + '\n- '.join(map(str, acceptance))
        return self.agent.engineering.run(
            task_request,
            research=False,
            max_steps=getattr(self.agent, 'max_steps', 12),
            max_attempts=2,
        )

    def run(self, max_rounds: int = 20, requested_workers: int | None = None) -> dict[str, Any]:
        state = self._load()
        if not state:
            return {'ok': False, 'status': 'not_prepared', 'error': 'prepare primeiro'}
        workers = requested_workers or 1
        # Never allow multiple workspace-changing engineering tasks to mutate
        # the same project concurrently. Explicitly parallel-safe tasks may use
        # the scheduler's normal capacity.
        if all(t.payload.get('parallel_safe') for t in self.tasks.tasks.values()
               if t.id in set(state.get('task_ids', []))):
            workers = max(1, min(4, int(workers)))
        else:
            workers = 1
        self.scheduler.max_workers = workers
        result = self.scheduler.run_monitored(
            self._runner, max_rounds=max_rounds, adaptive=True,
            requested_workers=workers, retries=0,
        )
        state['status'] = result.get('run', {}).get('status', 'unknown')
        state['last_run'] = result.get('run')
        state['updated_at'] = time.time()
        self._save(state)
        result['state'] = state
        return result

    def resume(self, max_rounds: int = 20, requested_workers: int | None = None) -> dict[str, Any]:
        return self.run(max_rounds=max_rounds, requested_workers=requested_workers)

    def status(self) -> dict[str, Any]:
        state = self._load()
        task_ids = set((state or {}).get('task_ids', []))
        tasks = [asdict(t) for t in self.tasks.tasks.values() if t.id in task_ids]
        counts = {}
        for t in tasks:
            counts[t['status']] = counts.get(t['status'], 0) + 1
        return {'ok': True, 'state': state, 'counts': counts, 'tasks': tasks,
                'scheduler': self.scheduler.status()}
