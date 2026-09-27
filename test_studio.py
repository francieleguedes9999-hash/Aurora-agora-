import tempfile
from pathlib import Path
from types import SimpleNamespace
from aurora.studio import AuroraStudio

class FakeAgent:
    def __init__(self, root):
        self.workspace=SimpleNamespace(root=root)
        self.calls=[]
    def _call(self, tool, args):
        self.calls.append((tool,args))
        if tool=='build_app': return {'ok':True,'specification':{'name':'X'}} if args.get('action')=='specification' else {'ok':True,'app':{'path':str(Path(self.workspace.root)/'x')}}
        if tool=='run_tests': return {'ok':True,'passed':True}
        if tool=='diagnose': return {'ok':True,'diagnosis':'none'}
        if tool=='deploy': return {'ok':True,'plan':True} if args.get('action')=='plan' else {'ok':True}
        raise AssertionError(tool)
    def run_cycle(self,*a,**k): return {'status':'completed','step':1}

def test_studio_basic_and_persistence():
    with tempfile.TemporaryDirectory() as d:
        a=FakeAgent(d); s=AuroraStudio(a)
        r=s.run('crie um app de tarefas')
        assert r['ok'] and r['status']=='completed'
        assert Path(d,'.aurora/studio.json').exists()
        assert s.status()['studio']['request']=='crie um app de tarefas'

def test_studio_deploy_dry_run():
    with tempfile.TemporaryDirectory() as d:
        a=FakeAgent(d); s=AuroraStudio(a)
        r=s.run('app', deploy=True, dry_run=True, deploy_config={'provider':'local','command':'echo {package}'})
        assert r['ok']
        assert any(x['stage']=='dry_run' for x in r['stages'])
