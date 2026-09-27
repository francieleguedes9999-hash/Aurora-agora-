import json
from aurora.agent import Agent
from aurora.core_loop import AgentCore
from aurora.model import Model

class SuccessModel(Model):
    def __init__(self): self.i = 0
    def ask(self, prompt):
        self.i += 1
        if self.i == 1:
            return json.dumps({"tool":"write_file","args":{"path":"app.txt","content":"ok"}})
        if self.i == 2:
            return json.dumps({"tool":"read_file","args":{"path":"app.txt"}})
        return json.dumps({"final":"feito"})

def test_core_observe_act(tmp_path):
    agent = Agent(tmp_path, model=SuccessModel())
    result = AgentCore(agent, max_steps=3).run("crie e verifique app.txt")
    assert result["status"] == "completed"
    assert (tmp_path / "app.txt").read_text() == "ok"
    assert len(result["observations"]) == 2

class FailureThenDiagnoseModel(Model):
    def __init__(self): self.i = 0
    def ask(self, prompt):
        self.i += 1
        if self.i == 1:
            return json.dumps({"tool":"run_command","args":{"command":"python -c \"raise ValueError('quebrou')\""}})
        if self.i == 2:
            return json.dumps({"tool":"write_file","args":{"path":"fix.txt","content":"corrigido"}})
        return json.dumps({"final":"corrigido"})

def test_core_injects_diagnostic_into_next_decision(tmp_path):
    model = FailureThenDiagnoseModel()
    agent = Agent(tmp_path, model=model)
    result = AgentCore(agent, max_steps=3).run("execute e corrija")
    assert result["status"] == "completed"
    first = result["observations"][0]
    assert first["diagnostic"]["kind"] == "value"
    assert (tmp_path / "fix.txt").exists()
