import json
from aurora.agent import Agent
from aurora.model import Model
from aurora.brain import CognitiveBrain

class BrainModel(Model):
    def __init__(self): self.i = 0
    def ask(self, prompt):
        self.i += 1
        if self.i == 1:
            return '```json\n{"tool":"write_file","args":{"path":"brain.txt","content":"Aurora"}}\n```'
        if self.i == 2:
            return json.dumps({"tool":"read_file","args":{"path":"brain.txt"}})
        return json.dumps({"final":"arquivo verificado"})
    def available(self): return True

def test_brain_builds_context_and_recovers_fenced_json(tmp_path):
    agent = Agent(tmp_path, model=BrainModel(), max_steps=3)
    result = agent.run_brain('crie e verifique brain.txt')
    assert result['status'] == 'completed'
    assert (tmp_path / 'brain.txt').read_text() == 'Aurora'
    assert len(result['history']) == 2

def test_brain_status(tmp_path):
    agent = Agent(tmp_path, model=BrainModel())
    status = agent.brain_status()
    assert status['model_available'] is True
    assert status['history_items'] == 0
