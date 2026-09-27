from pathlib import Path
from aurora.agent import Agent


def test_generated_frontend_materializes_declared_screens(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=4)
    result = a._call('app_build_coordinator', {
        'action': 'build_and_validate',
        'description': 'Crie um aplicativo de tarefas com login, cadastro e painel',
        'name': 'Tarefas UI 761',
    })
    assert result['ok']
    root = Path(result['app']['path'])
    html = (root / 'frontend' / 'index.html').read_text(encoding='utf-8')
    js = (root / 'frontend' / 'app.js').read_text(encoding='utf-8')
    contract = (root / 'frontend' / 'components.json').read_text(encoding='utf-8')
    assert 'screen-shell' in html
    assert 'renderScreenShell' in js
    assert 'screens' in js
    assert 'screens' in (root / 'preview' / 'preview.json').read_text(encoding='utf-8')
    assert 'data-list' in contract
