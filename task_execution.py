from __future__ import annotations
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from .task_decomposer import TaskDecomposer
from .task_manager import Task, TaskManager


@dataclass
class ExecutionState:
    id: str
    request: str
    decomposition_id: str
    status: str = "pending"
    rounds: int = 0
    completed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class TaskExecutionCoordinator:
    """Connects decomposition DAGs to the persistent TaskManager.

    The coordinator is intentionally model-agnostic: callers provide the runner
    for a single task. This keeps orchestration deterministic while allowing the
    Agent/AutonomousEngineering layer to supply model-powered execution.
    """
    def __init__(self, root: str | Path, decomposer: TaskDecomposer | None = None,
                 tasks: TaskManager | None = None):
        self.root = Path(root).resolve()
        self.decomposer = decomposer or TaskDecomposer(self.root)
        self.tasks = tasks or TaskManager(self.root)
        self.path = self.root / ".aurora" / "task-execution.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state: ExecutionState | None = self._load()

    def _load(self) -> ExecutionState | None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return ExecutionState(**raw)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _save(self) -> None:
        if not self.state:
            return
        self.state.updated_at = time.time()
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self.state), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def prepare(self, request: str, reuse: bool = True, replace: bool = False) -> dict[str, Any]:
        result = self.decomposer.decompose(request, reuse=reuse, replace=replace)
        if not result.get("ok"):
            return result
        dec = result["decomposition"]
        # Reuse a task graph only when it belongs to this decomposition.
        existing = {t.id: t for t in self.tasks.tasks.values()}
        created = []
        for item in dec["tasks"]:
            if item["id"] in existing:
                continue
            task = self.tasks.create(
                item["title"], kind="engineering", payload={
                    "stage": item["stage"],
                    "context_query": item["context_query"],
                    "acceptance": item["acceptance"],
                    "decomposition_id": dec["id"],
                }, depends_on=item.get("depends_on", []), task_id=item["id"])
            created.append(asdict(task))
        self.state = ExecutionState(
            id=uuid.uuid4().hex[:12], request=request.strip(),
            decomposition_id=dec["id"], status="ready",
            completed=[t["id"] for t in dec["tasks"] if t["status"] == "done"],
        )
        self._save()
        return {"ok": True, "reused": result.get("reused", False),
                "execution": asdict(self.state), "created_tasks": created,
                "decomposition": dec}

    @staticmethod
    def _ok(value: Any) -> bool:
        if isinstance(value, dict) and "ok" in value:
            return bool(value["ok"])
        if isinstance(value, dict) and "status" in value:
            return value["status"] not in {"failed", "error"}
        return bool(value)

    def run(self, runner: Callable[[Task], Any], max_rounds: int = 20) -> dict[str, Any]:
        if not self.state:
            return {"ok": False, "status": "not_prepared", "error": "prepare primeiro"}
        if self.state.status == "completed":
            return {"ok": True, "status": "completed", "execution": asdict(self.state), "reused": True}
        max_rounds = max(1, int(max_rounds))
        while self.state.rounds < max_rounds:
            ready = [t for t in self.tasks.ready()
                     if t.payload.get("decomposition_id") == self.state.decomposition_id]
            if not ready:
                dec = self.decomposer.status().get("decomposition")
                if dec and all(t.get("status") == "done" for t in dec.get("tasks", [])):
                    self.state.status = "completed"
                elif self.state.failed:
                    self.state.status = "failed"
                else:
                    self.state.status = "blocked"
                self._save()
                return {"ok": self.state.status == "completed", "status": self.state.status,
                        "execution": asdict(self.state)}
            self.state.rounds += 1
            # TaskManager handles persistence and dependency readiness. A single
            # round may execute independent tasks concurrently.
            executed = self.tasks.run_ready(runner, max_workers=self.tasks.max_workers)
            for task in executed:
                self.state.results[task.id] = task.result
                if task.status == "done":
                    if task.id not in self.state.completed:
                        self.state.completed.append(task.id)
                    self.decomposer.mark(task.id, "done")
                else:
                    if task.id not in self.state.failed:
                        self.state.failed.append(task.id)
                    self.decomposer.mark(task.id, "failed", task.error)
            self._save()
        self.state.status = "running"
        self._save()
        return {"ok": False, "status": "max_rounds", "execution": asdict(self.state)}

    def resume(self, runner: Callable[[Task], Any], max_rounds: int = 20) -> dict[str, Any]:
        return self.run(runner, max_rounds=max_rounds)

    def status(self) -> dict[str, Any]:
        return {"ok": True, "execution": asdict(self.state) if self.state else None,
                "task_manager": self.tasks.status(), "decomposition": self.decomposer.status()}
