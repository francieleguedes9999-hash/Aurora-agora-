import json
from aurora.app_builder import AppBuilder
from aurora.tools.test_runner import TestRunner


def test_build_uses_detailed_contract(tmp_path):
    b = AppBuilder(tmp_path, TestRunner(tmp_path))
    result = b.build('Crie um aplicativo de loja com login e cadastro de produtos em banco de dados', name='Loja Contrato')
    assert result['ok']
    root = tmp_path / 'apps' / 'loja-contrato'
    contract = json.loads((root / 'aurora.contract.json').read_text())
    assert any(x['path'] == '/api/products' for x in contract['endpoints'])
    assert (root / 'docs' / 'ACCEPTANCE.md').exists()
    assert (root / 'database' / 'entities.json').exists()
    html = (root / 'frontend' / 'index.html').read_text()
    assert '/products' in html


def test_detailed_build_is_explicitly_contract_driven(tmp_path):
    b = AppBuilder(tmp_path)
    result = b.build('Crie um aplicativo de tarefas com login e banco de dados', name='Tarefas Contrato', run_tests=False)
    root = tmp_path / 'apps' / 'tarefas-contrato'
    assert result['ok']
    routes = json.loads((root / 'backend' / 'routes.json').read_text())
    assert any(x['path'] == '/api/tasks' for x in routes)
