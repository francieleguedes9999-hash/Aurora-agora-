import tempfile
from pathlib import Path
from aurora.agent import Agent


def test_plan_is_non_mutating():
    with tempfile.TemporaryDirectory() as d:
        a=Agent(d)
        out=a._call('release_intelligence', {'action':'plan','label':'r'})
        assert out['ok'] and out['steps'][0]=='studio'
        assert not (Path(d)/'.aurora/release-intelligence.json').exists()


def test_empty_request_is_blocked():
    with tempfile.TemporaryDirectory() as d:
        a=Agent(d)
        out=a._call('release_intelligence', {'action':'run','request':''})
        assert not out['ok'] and out['status']=='invalid_request'


def test_failed_studio_does_not_create_release():
    with tempfile.TemporaryDirectory() as d:
        a=Agent(d)
        a.studio.run=lambda *args, **kwargs: {'ok':False,'status':'failed','artifacts':{},'errors':['x']}
        out=a._call('release_intelligence', {'action':'run','request':'create app'})
        assert not out['ok'] and out['status']=='blocked'
        assert out['reason']=='studio_failed'
        assert a.releases.status()['count']==0


def test_completed_cycle_creates_release(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        a=Agent(d)
        (Path(d)/'app.py').write_text('print(1)')
        a.studio.run=lambda *args, **kwargs: {'ok':True,'status':'completed','artifacts':{'tests':{'ok':True}}}
        out=a._call('release_intelligence', {'action':'run','request':'create app','label':'r'})
        assert out['ok'] and out['status']=='completed'
        assert out['release']['label']=='r'
        assert a.releases.status()['count']==1
