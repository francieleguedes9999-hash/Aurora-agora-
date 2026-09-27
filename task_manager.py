from __future__ import annotations
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Task:
    id: str
    title: str
    kind: str = "command"
    payload: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


class TaskManager:
    """Persistent DAG task manager with bounded parallel execution."""
    def __init__(self, root: str | Path, max_workers: int = 4):
        self.root = Path(root).resolve()
        self.path = self.root / ".aurora" / "tasks.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_workers = max(1, int(max_workers))
        self.tasks: dict[str, Task] = self._load()

    def _load(self) -> dict[str, Task]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return {k: Task(**v) for k, v in raw.items()}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        self.path.write_text(
            json.dumps({k: asdict(v) for k, v in self.tasks.items()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def create(self, title: str, kind: str = "command", payload: dict[str, Any] | None = None,
               depends_on: list[str] | None = None, task_id: str | None = None) -> Task:
        tid = task_id or uuid.uuid4().hex[:10]
        task = Task(tid, title.strip(), kind, payload or {}, depends_on or [])
        self.tasks[tid] = task
        self._save()
        return task

    def create_many(self, items: list[dict[str, Any]]) -> list[Task]:
        created = []
        for item in items:
            created.append(self.create(
                str(item.get("title", item.get("command", "Tarefa"))),
                str(item.get("kind", "command")),
                dict(item.get("payload") or ({"command": item["command"]} if "command" in item else {})),
                list(item.get("depends_on") or []),
                item.get("id"),
            ))
        return created

    def ready(self) -> list[Task]:
        done = {t.id for t in self.tasks.values() if t.status == "done"}
        return [t for t in self.tasks.values()
                if t.status == "pending" and all(dep in done for dep in t.depends_on)]

    def _mark_running(self, tasks: list[Task]) -> None:
        for task in tasks:
            task.status = "running"
            task.updated_at = _now()
        self._save()

    def run_ready(self, runner: Callable[[Task], Any], max_workers: int | None = None) -> list[Task]:
        ready = self.ready()
        if not ready:
            return []
        workers = min(max(1, max_workers or self.max_workers), len(ready))
        self._mark_running(ready)
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="aurora-task") as pool:
            futures = {pool.submit(runner, task): task for task in ready}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    task.result = future.result()
                    ok = not (isinstance(task.result, dict) and task.result.get("ok") is False)
                    task.status = "done" if ok else "failed"
                    if not ok:
                        task.error = str(task.result.get("error", "Tarefa falhou"))
                except Exception as exc:
                    task.status = "failed"
                    task.error = str(exc)
                task.updated_at = _now()
                self._save()
        return ready

    def retry_failed(self) -> list[Task]:
        failed = []
        for task in self.tasks.values():
            if task.status == "failed":
                task.status, task.error = "pending", ""
                task.result = None
                task.updated_at = _now()
                failed.append(task)
        self._save()
        return failed

    def status(self) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for task in self.tasks.values():
            counts[task.status] = counts.get(task.status, 0) + 1
        return {"counts": counts, "tasks": [asdict(t) for t in self.tasks.values()]}
