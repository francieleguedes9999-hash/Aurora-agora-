from pathlib import Path
from aurora.task_manager import TaskManager


def test_parallel_tasks_persist_and_respect_dependencies(tmp_path: Path):
    tm = TaskManager(tmp_path, max_workers=2)
    a = tm.create("a", payload={"command": "echo a"})
    b = tm.create("b", payload={"command": "echo b"})
    c = tm.create("c", payload={"command": "echo c"}, depends_on=[a.id, b.id])
    ran = []
    tm.run_ready(lambda t: ran.append(t.id) or {"ok": True, "id": t.id})
    assert set(ran) == {a.id, b.id}
    assert tm.tasks[a.id].status == tm.tasks[b.id].status == "done"
    tm.run_ready(lambda t: {"ok": True, "id": t.id})
    assert tm.tasks[c.id].status == "done"
    assert (tmp_path / ".aurora" / "tasks.json").exists()


def test_failed_task_can_be_retried(tmp_path: Path):
    tm = TaskManager(tmp_path)
    t = tm.create("bad", payload={"command": "false"})
    tm.run_ready(lambda _: {"ok": False, "error": "boom"})
    assert tm.tasks[t.id].status == "failed"
    tm.retry_failed()
    assert tm.tasks[t.id].status == "pending"
