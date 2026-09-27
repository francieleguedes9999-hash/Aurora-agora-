import json
from aurora.research import Researcher
from aurora.agent import Agent
from aurora.model import Model

class FakeModel(Model):
    def __init__(self): self.i=0
    def ask(self, prompt):
        self.i += 1
        if self.i == 1: return json.dumps({'tool':'research','args':{'query':'como criar uma API REST'}})
        return json.dumps({'final':'Pesquisa recebida e processada.'})

def test_research_fallback_is_explicit():
    r=Researcher(command=None)
    out=r.search('teste')
    assert out['available'] is False

def test_agent_can_use_research_tool(tmp_path):
    out=Agent(workspace=tmp_path, model=FakeModel(), max_steps=2).run('pesquise')
    assert out['status']=='completed'
    assert out['history'][0]['tool']=='research'
    assert out['history'][0]['result']['available'] is False
