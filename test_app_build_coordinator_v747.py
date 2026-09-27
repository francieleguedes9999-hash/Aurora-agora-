from aurora.agent import Agent


def test_build_and_validate_generates_app(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=4)
    r = a._call('app_build_coordinator', {'action':'build_and_validate','description':'Crie um aplicativo de tarefas com login e banco de dados','name':'Tarefas 747'})
    assert r['ok']
    assert r['app']['path']
    assert r['validation']['tests'] is not None
    assert 'visual_contract' in r['validation']


def test_coordinator_status(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=2)
    r = a._call('app_build_coordinator', {'action':'status'})
    assert r['ok']
    assert r['last'] is None


def test_create_app_runs_blueprint_and_build_pipeline(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=4)
    r = a._call('app_build_coordinator', {
        'action': 'create_app',
        'description': 'Crie um aplicativo de tarefas com cadastro e banco de dados',
        'name': 'Tarefas Pipeline 757',
        'research': False,
    })
    assert r['ok']
    assert r['status'] == 'completed'
    assert r['blueprint']['status'] == 'ready'
    assert r['app']['path']
    assert r['validation']['tests'] is not None


def test_create_app_rejects_empty_description(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=2)
    r = a._call('app_build_coordinator', {'action': 'create_app', 'description': ''})
    assert not r['ok']
    assert r['status'] == 'invalid_request'
