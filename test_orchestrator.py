from pathlib import Path
from aurora.agent import Agent


def test_orchestrator_plan(tmp_path):
    a=Agent(tmp_path)
    out=a._call('orchestrator', {'action':'plan','request':'criar app'})
    assert out['ok'] and out['stages'][0]=='studio'


def test_orchestrator_reuses_identical_completed_run(tmp_path):
    a=Agent(tmp_path)
    a.studio.run=lambda *args, **kwargs: {'ok':True,'status':'completed','artifacts':{'tests':{'ok':True}},'stages':[]}
    first=a._call('orchestrator', {'action':'run','request':'criar app'})
    assert first['ok']
    second=a._call('orchestrator', {'action':'run','request':'criar app'})
    assert second['ok']
    assert second['outputs']['reused_run_id']==first['orchestrator_id']


def test_orchestrator_failure_is_persisted(tmp_path):
    a=Agent(tmp_path)
    a.studio.run=lambda *args, **kwargs: {'ok':False,'status':'failed','errors':['x']}
    out=a._call('orchestrator', {'action':'run','request':'criar app'})
    assert not out['ok'] and out['status']=='failed'
    assert Path(tmp_path,'.aurora/orchestrator.json').exists()
