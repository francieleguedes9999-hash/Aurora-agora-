import json
from pathlib import Path
from aurora.deploy import DeployManager


def test_validate_and_dry_run(tmp_path):
    d=DeployManager(tmp_path)
    cfg={"provider":"local","environment":"test","command":"python -c \"print('ok')\""}
    assert d.validate(cfg)["ok"]
    out=d.deploy(cfg, dry_run=True)
    assert out["ok"] and out["dry_run"]
    assert not (tmp_path/'.aurora/deploy.json').exists()


def test_local_deploy_persists_state_and_rollback(tmp_path):
    d=DeployManager(tmp_path)
    cfg={"provider":"local","environment":"test","command":"python -c \"open('deployed.txt','w').write('1')\""}
    first=d.deploy(cfg)
    assert first["ok"]
    assert (tmp_path/'deployed.txt').exists()
    cfg2={"provider":"local","environment":"test","command":"python -c \"open('deployed.txt','w').write('2')\""}
    second=d.deploy(cfg2)
    assert second["ok"]
    assert (tmp_path/'deployed.txt').read_text()=='2'
    rb=d.rollback({"provider":"local","environment":"test","command":"python -c \"open('deployed.txt','w').write('rollback')\""})
    assert rb["ok"]
    state=d.status()
    assert state["current"] is not None


def test_invalid_docker_and_secret_not_persisted(tmp_path):
    d=DeployManager(tmp_path)
    bad=d.validate({"provider":"docker","environment":"test"})
    assert not bad["ok"]
    assert "Dockerfile" in bad["errors"][0] or "compose" in bad["errors"][0]
    cfg={"provider":"local","environment":"test","command":"python -c \"print('token=SECRET')\""}
    assert d.deploy(cfg)["ok"]
    text=(tmp_path/'.aurora/deploy-history.jsonl').read_text()
    assert 'SECRET' not in text
