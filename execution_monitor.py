from __future__ import annotations
import json, threading, time, uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from typing import Any, Callable

class ExecutionMonitor:
    """Persistent monitor for bounded task execution, retries and cooperative cancellation."""
    def __init__(self, root: str | Path, max_history: int = 100):
        self.root = Path(root).resolve()
        self.path = self.root / '.aurora' / 'execution_monitor.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_history = max_history
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self.state = self._load()

    def _load(self):
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return {'runs': [], 'active': None}

    def _save(self):
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding='utf-8')

    def cancel(self) -> dict[str, Any]:
        self._cancel.set()
        with self._lock:
            active = self.state.get('active')
            if active:
                active['cancel_requested'] = True
                self._save()
        return {'ok': True, 'cancel_requested': True}

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {'ok': True, 'active': self.state.get('active'), 'runs': self.state.get('runs', [])[-20:]}

    def _record_event(self, run: dict[str, Any], event: str, **data):
        run.setdefault('events', []).append({'event': event, 'timestamp': time.time(), **data})

    def run(self, fn: Callable[[], Any], *, name: str = 'task', timeout: float | None = None,
            retries: int = 0, retry_delay: float = 0.0) -> dict[str, Any]:
        run_id = uuid.uuid4().hex[:12]
        retries = max(0, int(retries)); timeout = None if timeout is None else max(0.01, float(timeout))
        record = {'id': run_id, 'name': name, 'status': 'running', 'started_at': time.time(),
                  'attempts': [], 'cancel_requested': False}
        with self._lock:
            self._cancel.clear(); self.state['active'] = record; self._save()
        final = None
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='aurora-monitor')
        try:
            for attempt in range(1, retries + 2):
                if self._cancel.is_set():
                    record['status'] = 'cancelled'; break
                started = time.time(); self._record_event(record, 'attempt_started', attempt=attempt)
                future = executor.submit(fn)
                try:
                    result = future.result(timeout=timeout)
                    elapsed = time.time() - started
                    ok = not (isinstance(result, dict) and result.get('ok') is False)
                    attempt_record = {'attempt': attempt, 'status': 'completed' if ok else 'failed',
                                      'duration_seconds': round(elapsed, 6), 'result': result}
                    record['attempts'].append(attempt_record); final = result
                    if ok:
                        record['status'] = 'completed'; break
                    record['status'] = 'failed'
                except TimeoutError:
                    elapsed = time.time() - started
                    record['attempts'].append({'attempt': attempt, 'status': 'timeout',
                                              'duration_seconds': round(elapsed, 6)})
                    record['status'] = 'timeout'; final = {'ok': False, 'timed_out': True, 'error': 'execution timeout'}
                except Exception as exc:
                    record['attempts'].append({'attempt': attempt, 'status': 'failed',
                                              'duration_seconds': round(time.time()-started, 6), 'error': str(exc)})
                    record['status'] = 'failed'; final = {'ok': False, 'error': str(exc)}
                if attempt <= retries and not self._cancel.is_set():
                    record['status'] = 'retrying'; self._record_event(record, 'retry_scheduled', attempt=attempt)
                    if retry_delay: time.sleep(max(0.0, float(retry_delay)))
            if self._cancel.is_set() and record['status'] not in {'completed'}:
                record['status'] = 'cancelled'; final = {'ok': False, 'cancelled': True}
        finally:
            # A timed-out callable may still be finishing; shutdown(wait=False) avoids blocking the monitor.
            executor.shutdown(wait=False, cancel_futures=True)
            record['finished_at'] = time.time()
            record['duration_seconds'] = round(record['finished_at'] - record['started_at'], 6)
            with self._lock:
                self.state.setdefault('runs', []).append(record)
                self.state['runs'] = self.state['runs'][-self.max_history:]
                self.state['active'] = None
                self._save()
        return {'ok': record['status'] == 'completed', 'run': record, 'result': final}

    def run_command(self, terminal, command: str, cwd: str | None = None, *, timeout: float | None = None,
                    retries: int = 0) -> dict[str, Any]:
        return self.run(lambda: terminal.run(command, cwd), name=command, timeout=timeout,
                        retries=retries)
