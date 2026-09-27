from aurora.scheduler import ParallelScheduler
from aurora.task_manager import TaskManager

def test_adaptive_plan_respects_heavy_tasks(tmp_path):
    tm = TaskManager(tmp_path, max_workers=8)
    tm.create("heavy", payload={"resource_class":"heavy"}, task_id="heavy")
    tm.create("normal", payload={"resource_class":"normal"}, task_id="normal")
    s = ParallelScheduler(tmp_path, tm, 8)
    p = s.adaptive_plan(8)
    assert p["ok"] and p["recommended_workers"] >= 1
    assert len(p["selected"]) <= p["recommended_workers"]

def test_adaptive_run_persists_resource_decision(tmp_path):
    tm = TaskManager(tmp_path, max_workers=2)
    tm.create("a", payload={"resource_class":"normal"}, task_id="a")
    tm.create("b", payload={"resource_class":"normal"}, task_id="b")
    s = ParallelScheduler(tmp_path, tm, 2)
    out = s.run_adaptive(lambda t: {"ok": True, "id": t.id}, max_rounds=3)
    assert out["ok"]
    assert out["run"]["mode"] == "adaptive"
    assert out["run"]["batches"][0]["recommended_workers"] >= 1
