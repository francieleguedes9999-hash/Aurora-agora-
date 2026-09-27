from aurora.agent import Agent


def test_evolution_prepares_modules_from_generated_app(tmp_path):
    a = Agent(str(tmp_path))
    built = a.app_builder.build('Criar aplicativo de cadastro com login e banco de dados', run_tests=False)
    assert built['ok']
    spec = built['spec']
    result = a._call('app_evolution', {'action': 'prepare', 'spec': spec, 'blueprint_id': 'bp1'})
    assert result['ok']
    ids = {m['id'] for m in result['state']['modules']}
    assert 'mod_frontend' in ids
    assert 'mod_backend' in ids
    assert 'mod_data' in ids
    assert 'mod_quality' in ids


def test_evolution_prompt_and_mark_are_persistent(tmp_path):
    a = Agent(str(tmp_path))
    built = a.app_builder.build('Criar app simples', run_tests=False)
    a._call('app_evolution', {'action': 'prepare', 'spec': built['spec']})
    prompt = a._call('app_evolution', {'action': 'prompt', 'module_id': 'mod_frontend'})
    assert prompt['ok']
    assert 'frontend' in prompt['prompt']
    marked = a._call('app_evolution', {'action': 'mark', 'module_id': 'mod_frontend', 'status': 'done'})
    assert marked['ok']
    status = a._call('app_evolution', {'action': 'status'})
    assert status['state']['modules'][0]['status'] == 'done'
