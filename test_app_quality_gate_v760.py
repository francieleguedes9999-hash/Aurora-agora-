from aurora.agent import Agent
from aurora.app_quality_gate import AppQualityGate


def test_quality_gate_accepts_generated_app(tmp_path):
    a = Agent(workspace=str(tmp_path), max_steps=4)
    r = a._call('app_build_coordinator', {
        'action': 'build_and_validate',
        'description': 'Crie um aplicativo de tarefas com cadastro e banco de dados',
        'name': 'Tarefas Quality 760',
    })
    assert r['ok']
    q = r['validation']['quality_gate']
    assert q['ok']
    assert q['checks']['required_files']['ok']
    assert q['checks']['python_syntax']['ok']
    assert q['checks']['html']['ok']
    assert q['checks']['interactive_preview']['ok']


def test_quality_gate_detects_missing_preview(tmp_path):
    root = tmp_path / 'app'
    root.mkdir()
    for rel in AppQualityGate.REQUIRED:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('<!doctype html><button>ok</button>' if rel.endswith('.html') else '', encoding='utf-8')
    (root / 'preview' / 'index.html').unlink()
    result = AppQualityGate().inspect(root)
    assert not result['ok']
    assert 'preview/index.html' in result['checks']['required_files']['missing']
