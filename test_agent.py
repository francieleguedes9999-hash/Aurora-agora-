import json
from aurora.agent import Agent
from aurora.model import Model
class DemoModel(Model):
    def __init__(self): self.i=0
    def ask(self,prompt):
        self.i+=1
        if self.i==1: return json.dumps({'tool':'write_file','args':{'path':'hello.txt','content':'Aurora'}})
        if self.i==2: return json.dumps({'tool':'read_file','args':{'path':'hello.txt'}})
        return json.dumps({'final':'Arquivo criado e verificado.'})
def test_agent_loop(tmp_path):
    r=Agent(tmp_path,model=DemoModel(),max_steps=3).run('crie hello')
    assert r['status']=='completed'
    assert (tmp_path/'hello.txt').read_text()=='Aurora'
