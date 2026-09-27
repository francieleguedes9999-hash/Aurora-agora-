from aurora.agent import Agent


def test_affected_modules_maps_changed_files(tmp_path):
    a = Agent(str(tmp_path))
    built = a.app_builder.build('Criar app simples', run_tests=False)
    a._call('app_evolution', {'action': 'prepare', 'spec': built['spec']})
    result = a._call('app_evolution', {'action': 'affected_modules', 'comparison': {'actual_files': ['frontend/index.html']}})
    assert result['ok']
    assert any(x['key'] == 'frontend' for x in result['affected_modules'])


def test_regression_plan_is_focused(tmp_path):
    a = Agent(str(tmp_path))
    built = a.app_builder.build('Criar aplicativo com banco de dados', run_tests=False)
    a._call('app_evolution', {'action': 'prepare', 'spec': built['spec']})
    result = a._call('app_evolution', {'action': 'regression_plan', 'comparison': {'actual_files': ['backend/main.py']}})
    assert result['ok']
    assert any(x['key'] == 'backend' for x in result['affected_modules'])
