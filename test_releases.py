import tempfile
from pathlib import Path
from aurora.releases import ReleaseManager


def test_create_release_links_version_and_artifact():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'app.py').write_text('print(1)')
        m=ReleaseManager(root)
        result=m.create('first')
        assert result['ok']
        rel=result['release']
        assert rel['version_id'] and rel['artifact_id']
        assert m.status()['count']==1
        assert m.artifacts.verify(rel['artifact_id'])['ok']


def test_release_plan_is_non_mutating():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'x.txt').write_text('x')
        m=ReleaseManager(root)
        plan=m.plan('preview')
        assert plan['ok'] and not (root/'.aurora/releases/state.json').exists()


def test_dry_run_release_deploy_does_not_change_release():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'x.txt').write_text('x')
        m=ReleaseManager(root); rel=m.create('r')['release']
        cfg={'provider':'local','command':'true','environment':'test'}
        out=m.deploy(rel['id'], cfg, dry_run=True)
        assert out['ok'] and out['deployment']['dry_run'] is True
        assert m._get(rel['id'])['status']=='created'
