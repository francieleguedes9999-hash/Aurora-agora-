import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))

from aurora.app_builder import AppBuilder


def test_detailed_screens_are_materialized_and_bound_to_entities(tmp_path):
    builder = AppBuilder(tmp_path)
    result = builder.build('Crie uma loja de produtos com cadastro, login e estoque', name='Loja Funcional', run_tests=False)
    assert result['ok']
    root = Path(result['app']['path'])
    contract = json.loads((root / 'aurora.contract.json').read_text(encoding='utf-8'))
    html = (root / 'frontend' / 'index.html').read_text(encoding='utf-8')
    js = (root / 'frontend' / 'app.js').read_text(encoding='utf-8')
    assert contract['screens']
    assert any(s['id'] == 'catalog' for s in contract['screens'])
    assert 'SCREEN_ENTITY_HINTS' in js
    assert 'renderScreenContent' in js
    assert 'Product' in js
    assert 'screenEntity(screen)' in js
    assert '<nav>' in html


def test_screen_contract_is_present_in_generated_preview(tmp_path):
    builder = AppBuilder(tmp_path)
    result = builder.build('Crie um aplicativo de tarefas com login', name='Tarefas Funcionais', run_tests=False)
    root = Path(result['app']['path'])
    preview = json.loads((root / 'preview' / 'preview.json').read_text(encoding='utf-8'))
    assert any(s['id'] == 'tasks' for s in preview['screens'])
    assert any(e['name'] == 'Task' for e in preview['entities'])
