from aurora.agent import Agent

def test_orchestrator_build_gate_creates_real_app(tmp_path):
    a = Agent(str(tmp_path))
    prepared = a._call("project_orchestrator", {"action":"prepare", "request":"Criar aplicativo de tarefas com login e banco de dados", "research":False})
    assert prepared["ok"]
    build = next(x for x in prepared["created_tasks"] if x["payload"]["stage"] == "build")
    result = a.project_orchestrator._runner(a.project_orchestrator.tasks.tasks[build["id"]])
    assert result["ok"]
    assert (tmp_path / "apps").exists()
    assert any((tmp_path / "apps").iterdir())

def test_blueprint_build_gate_precedes_implementation(tmp_path):
    a = Agent(str(tmp_path))
    result = a._call("project_orchestrator", {"action":"prepare", "request":"Criar app de notas", "research":False})
    tasks = result["created_tasks"]
    build = next(x for x in tasks if x["payload"]["stage"] == "build")
    implementation = [x for x in tasks if x["payload"]["stage"] == "implementation"]
    assert implementation
    assert all(build["id"] in x["depends_on"] for x in implementation)
