from aurora.agent import Agent


def test_module_validation_runs_focused_gate(tmp_path):
    a = Agent(str(tmp_path))
    built = a.app_builder.build('Criar app simples', run_tests=False)
    a._call('app_evolution', {'action': 'prepare', 'spec': built['spec']})
    result = a._call('app_evolution', {'action': 'validate', 'module_id': 'mod_frontend'})
    assert result['ok']
    assert result['checks'][0]['name'] == 'frontend_presence'


def test_module_validation_backend_and_data(tmp_path):
    a = Agent(str(tmp_path))
    built = a.app_builder.build('Criar aplicativo com banco de dados', run_tests=False)
    a._call('app_evolution', {'action': 'prepare', 'spec': built['spec']})
    backend = a._call('app_evolution', {'action': 'validate', 'module_id': 'mod_backend'})
    data = a._call('app_evolution', {'action': 'validate', 'module_id': 'mod_data'})
    assert backend['ok']
    assert data['ok']


def test_orchestrator_module_stage_has_validation_result(tmp_path):
    a = Agent(str(tmp_path))
    prepared = a._call('project_orchestrator', {'action': 'prepare', 'request': 'Criar app simples', 'research': False})
    assert prepared['ok']
    task = next(x for x in prepared['created_tasks'] if x['payload']['stage'] == 'module_evolution')
    a.engineering.run = lambda *args, **kwargs: {'ok': True, 'status': 'completed'}
    result = a.project_orchestrator._runner(a.project_orchestrator.tasks.tasks[task['id']])
    assert result['history']
    assert 'validation' in result['history'][-1]
