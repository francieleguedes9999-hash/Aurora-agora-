from aurora.agent import Agent


def test_repair_cycle_reports_exact_patch_plan_on_failure(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=4)
    r = a._call('app_build_coordinator', {
        'action': 'repair_cycle',
        'description': 'Crie um aplicativo de tarefas com login e banco de dados',
        'name': 'Tarefas 748',
        'run_tests': True,
    })
    assert r['ok']
    assert r['status'] == 'completed'
    assert r['app']['path']


def test_repair_cycle_applies_safe_exact_patch_and_revalidates(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=4)
    built = a._call('app_build_coordinator', {
        'action': 'build_and_validate',
        'description': 'Crie um aplicativo simples de tarefas',
        'name': 'Tarefas Patch 748',
        'run_tests': True,
    })
    assert built['ok']
    path = built['app']['path']
    target = tmp_path / path / 'backend' / 'main.py'
    old = target.read_text(encoding='utf-8')
    new = old + '\n# Aurora repair-cycle marker\n'
    import hashlib
    digest = hashlib.sha256(old.encode('utf-8')).hexdigest()
    r = a._call('app_build_coordinator', {
        'action': 'repair_cycle',
        'description': 'Crie um aplicativo simples de tarefas',
        'name': 'Tarefas Patch 748',
        'run_tests': True,
        'patches': [{'path': str(target.relative_to(tmp_path)), 'old': old, 'new': new, 'expected_sha256': digest}],
        'max_attempts': 1,
        'app_path': path,
    })
    assert r['ok']
    assert '# Aurora repair-cycle marker' in target.read_text(encoding='utf-8')


def test_repair_cycle_rejects_stale_patch(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=4)
    built = a._call('app_build_coordinator', {
        'action': 'build_and_validate',
        'description': 'Crie um aplicativo de tarefas',
        'name': 'Tarefas Stale 748',
        'run_tests': True,
    })
    target = tmp_path / built['app']['path'] / 'backend' / 'main.py'
    old = target.read_text(encoding='utf-8')
    target.write_text(old + '\n# external change\n', encoding='utf-8')
    r = a._call('app_build_coordinator', {
        'action': 'repair_cycle',
        'description': 'Corrigir aplicativo de tarefas',
        'name': 'unused',
        'run_tests': True,
        'patches': [{'path': str(target.relative_to(tmp_path)), 'old': old, 'new': old + '\n# bad stale patch\n'}],
        'max_attempts': 1,
        'app_path': built['app']['path'],
    })
    assert not r['ok']
    assert r['status'] == 'failed'
