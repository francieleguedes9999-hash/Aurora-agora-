from pathlib import Path
from aurora.agent import Agent


def test_generated_screens_are_interactive_and_route_aware(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=4)
    result = a._call('app_build_coordinator', {
        'action': 'build_and_validate',
        'description': 'Crie um aplicativo de tarefas com tela inicial, cadastro de tarefas e painel',
        'name': 'Tarefas Navegacao 762',
    })
    assert result['ok']
    root = Path(result['app']['path'])
    js = (root / 'frontend' / 'app.js').read_text(encoding='utf-8')
    assert 'history.replaceState' in js
    assert 'screen-workspace' in js
    assert 'location.hash' in js
    assert 'Tela aberta:' in js
