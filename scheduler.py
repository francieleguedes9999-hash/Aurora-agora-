from __future__ import annotations
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .task_manager import TaskManager, Task
from .resource_intelligence import ResourceIntelligence
from .execution_monitor import ExecutionMonitor

class ParallelScheduler:
    """Dependency-aware scheduler with priorities and coarse resource locks."""
    def __init__(self, root: str | Path, tasks: TaskManager | None = None, max_workers: int = 4):
        self.root = Path(root).resolve()
        self.tasks = tasks or TaskManager(self.root, max_workers=max_workers)
        self.max_workers = max(1, int(max_workers))
        self.resources = ResourceIntelligence(self.root)
        self.path = self.root / '.aurora' / 'scheduler.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        try: return json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError): return {'runs': [], 'active': None}

    def _save(self):
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding='utf-8')

    @staticmethod
    def _priority(t: Task) -> int:
        try: return int(t.payload.get('priority', 0))
        except (TypeError, ValueError): return 0

    @staticmethod
    def _resources(t: Task) -> set[str]:
        raw = t.payload.get('resources', [])
        if isinstance(raw, str): raw = [raw]
        return {str(x) for x in raw if str(x)}

    def _select_batch(self, ready: list[Task], capacity: int) -> list[Task]:
        selected, locked = [], set()
        for task in sorted(ready, key=lambda t: (-self._priority(t), t.id)):
            resources = self._resources(task)
            if resources & locked:
                continue
            selected.append(task); locked |= resources
            if len(selected) >= capacity: break
        return selected

    def plan(self) -> dict[str, Any]:
        ready = self.tasks.ready()
        batch = self._select_batch(ready, self.max_workers)
        return {'ok': True, 'ready': [asdict(t) for t in ready], 'selected': [asdict(t) for t in batch],
                'max_workers': self.max_workers}

    def run(self, runner: Callable[[Task], Any], max_rounds: int = 20) -> dict[str, Any]:
        run_id = f'{int(time.time())}-{len(self.state.get("runs", []))+1}'
        record = {'id': run_id, 'started_at': time.time(), 'rounds': 0, 'batches': [], 'status': 'running'}
        self.state['active'] = run_id; self._save()
        for _ in range(max(1, int(max_rounds))):
            ready = self.tasks.ready()
            if not ready:
                record['status'] = 'completed' if all(t.status == 'done' for t in self.tasks.tasks.values()) else 'blocked'
                break
            batch = self._select_batch(ready, self.max_workers)
            if not batch: record['status'] = 'blocked'; break
            for t in batch: t.status = 'running'
            self.tasks._save()
            outcomes = []
            with ThreadPoolExecutor(max_workers=len(batch), thread_name_prefix='aurora-scheduler') as pool:
                futures = {pool.submit(runner, t): t for t in batch}
                for f in as_completed(futures):
                    t = futures[f]
                    try:
                        t.result = f.result()
                        ok = not (isinstance(t.result, dict) and t.result.get('ok') is False)
                        t.status = 'done' if ok else 'failed'
                        if not ok: t.error = str(t.result.get('error', 'tarefa falhou'))
                    except Exception as exc:
                        t.status, t.error = 'failed', str(exc)
                    outcomes.append({'id': t.id, 'status': t.status, 'result': t.result, 'error': t.error})
            self.tasks._save()
            record['rounds'] += 1; record['batches'].append(outcomes)
            if any(x['status'] == 'failed' for x in outcomes):
                record['status'] = 'failed'; break
        else: record['status'] = 'max_rounds'
        record['finished_at'] = time.time()
        self.state.setdefault('runs', []).append(record); self.state['active'] = None; self._save()
        return {'ok': record['status'] == 'completed', 'run': record}

    def adaptive_plan(self, requested_workers: int | None = None) -> dict[str, Any]:
        """Plan a batch using current machine capacity and task resource classes."""
        ready = self.tasks.ready()
        tasks = [asdict(t) for t in ready]
        recommendation = self.resources.recommend_workers(requested_workers or self.max_workers, tasks)
        capacity = max(1, min(self.max_workers, recommendation["recommended"], len(ready) or 1))
        batch = self._select_batch(ready, capacity)
        return {
            "ok": True, "ready": tasks, "selected": [asdict(t) for t in batch],
            "max_workers": self.max_workers, "recommended_workers": recommendation["recommended"],
            "resource": recommendation,
        }

    def run_adaptive(self, runner: Callable[[Task], Any], max_rounds: int = 20,
                     requested_workers: int | None = None) -> dict[str, Any]:
        """Execute dependency-ready work while adapting worker count each round."""
        run_id = f'adaptive-{int(time.time())}-{len(self.state.get("runs", []))+1}'
        record = {"id": run_id, "mode": "adaptive", "started_at": time.time(),
                  "rounds": 0, "batches": [], "status": "running"}
        self.state['active'] = run_id; self._save()
        for _ in range(max(1, int(max_rounds))):
            ready = self.tasks.ready()
            if not ready:
                record['status'] = 'completed' if all(t.status == 'done' for t in self.tasks.tasks.values()) else 'blocked'
                break
            recommendation = self.resources.recommend_workers(requested_workers or self.max_workers, [asdict(t) for t in ready])
            capacity = max(1, min(self.max_workers, recommendation['recommended'], len(ready)))
            batch = self._select_batch(ready, capacity)
            if not batch:
                record['status'] = 'blocked'; break
            for t in batch: t.status = 'running'
            self.tasks._save()
            outcomes = []
            started = time.time()
            with ThreadPoolExecutor(max_workers=len(batch), thread_name_prefix='aurora-adaptive') as pool:
                futures = {pool.submit(runner, t): t for t in batch}
                for f in as_completed(futures):
                    t = futures[f]
                    try:
                        t.result = f.result()
                        ok = not (isinstance(t.result, dict) and t.result.get('ok') is False)
                        t.status = 'done' if ok else 'failed'
                        if not ok: t.error = str(t.result.get('error', 'tarefa falhou'))
                    except Exception as exc:
                        t.status, t.error = 'failed', str(exc)
                    outcomes.append({'id': t.id, 'status': t.status, 'result': t.result, 'error': t.error})
            self.tasks._save()
            record['rounds'] += 1
            record['batches'].append({'workers': len(batch), 'recommended_workers': recommendation['recommended'],
                                      'duration_seconds': round(time.time()-started, 6), 'outcomes': outcomes})
            if any(x['status'] == 'failed' for x in outcomes):
                record['status'] = 'failed'; break
        else:
            record['status'] = 'max_rounds'
        record['finished_at'] = time.time()
        self.state.setdefault('runs', []).append(record); self.state['active'] = None; self._save()
        return {'ok': record['status'] == 'completed', 'run': record}

    def run_monitored(self, runner: Callable[[Task], Any], max_rounds: int = 20,
                      timeout: float | None = None, retries: int = 0,
                      retry_delay: float = 0.0, requested_workers: int | None = None,
                      adaptive: bool = True) -> dict[str, Any]:
        """Run dependency-ready tasks through an ExecutionMonitor per task.

        Each task gets an isolated monitor state so concurrent tasks do not overwrite
        one another. Timeouts/retries are converted into normal Task outcomes, while
        the scheduler continues with independent work only when the whole batch has
        completed. This is intentionally bounded and does not force-kill arbitrary
        Python callables; external commands should use SafeTerminal timeouts too.
        """
        run_id = f'monitored-{int(time.time())}-{len(self.state.get("runs", []))+1}'
        record = {'id': run_id, 'mode': 'adaptive-monitored' if adaptive else 'monitored',
                  'started_at': time.time(), 'rounds': 0, 'batches': [], 'status': 'running',
                  'timeout': timeout, 'retries': max(0, int(retries))}
        self.state['active'] = run_id; self._save()
        base = self.root / '.aurora' / 'scheduler_monitors'
        base.mkdir(parents=True, exist_ok=True)
        try:
            for _ in range(max(1, int(max_rounds))):
                ready = self.tasks.ready()
                if not ready:
                    record['status'] = 'completed' if all(t.status == 'done' for t in self.tasks.tasks.values()) else 'blocked'
                    break
                if adaptive:
                    rec = self.resources.recommend_workers(requested_workers or self.max_workers, [asdict(t) for t in ready])
                    capacity = max(1, min(self.max_workers, rec['recommended'], len(ready)))
                else:
                    rec = None; capacity = min(self.max_workers, len(ready))
                batch = self._select_batch(ready, capacity)
                if not batch:
                    record['status'] = 'blocked'; break
                for t in batch: t.status = 'running'
                self.tasks._save()
                started = time.time(); outcomes = []
                def monitored(task):
                    monitor_root = base / task.id
                    monitor = ExecutionMonitor(monitor_root)
                    result = monitor.run(lambda: runner(task), name=task.title, timeout=timeout,
                                         retries=retries, retry_delay=retry_delay)
                    return result
                with ThreadPoolExecutor(max_workers=len(batch), thread_name_prefix='aurora-monitored') as pool:
                    futures = {pool.submit(monitored, t): t for t in batch}
                    for f in as_completed(futures):
                        t = futures[f]
                        try:
                            monitored_result = f.result()
                            ok = bool(monitored_result.get('ok'))
                            t.result = monitored_result.get('result')
                            if ok:
                                t.status = 'done'; t.error = ''
                            else:
                                t.status = 'failed'
                                run = monitored_result.get('run', {})
                                t.error = str(run.get('status') or monitored_result.get('error') or 'tarefa falhou')
                            outcome = {'id': t.id, 'status': t.status, 'monitor': monitored_result.get('run'),
                                       'result': t.result, 'error': t.error}
                        except Exception as exc:
                            t.status = 'failed'; t.error = str(exc)
                            outcome = {'id': t.id, 'status': t.status, 'error': t.error}
                        t.updated_at = getattr(t, 'updated_at', None)
                        outcomes.append(outcome)
                self.tasks._save(); record['rounds'] += 1
                batch_record = {'duration_seconds': round(time.time()-started, 6), 'outcomes': outcomes,
                                'workers': len(batch), 'recommended_workers': (rec or {}).get('recommended', len(batch))}
                record['batches'].append(batch_record)
                if any(x['status'] == 'failed' for x in outcomes):
                    record['status'] = 'failed'; break
            else:
                record['status'] = 'max_rounds'
        finally:
            record['finished_at'] = time.time()
            self.state.setdefault('runs', []).append(record); self.state['active'] = None; self._save()
        return {'ok': record['status'] == 'completed', 'run': record}

    def status(self) -> dict[str, Any]:
        return {'ok': True, 'active': self.state.get('active'), 'runs': self.state.get('runs', [])[-20:], 'plan': self.plan()}
