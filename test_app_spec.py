from aurora.app_builder import AppBuilder
from aurora.app_spec import DetailedSpecBuilder

def test_detailed_spec_contains_screens_entities_endpoints_and_criteria(tmp_path):
    b = DetailedSpecBuilder(tmp_path)
    spec = b.build('Crie um aplicativo de loja com login e cadastro de produtos em banco de dados')
    assert spec.screens
    assert any(e.name == 'Product' for e in spec.entities)
    assert any(x.path == '/api/products' for x in spec.endpoints)
    assert spec.user_flows
    assert spec.acceptance_criteria
    assert (tmp_path / '.aurora' / 'app-spec.json').exists()

def test_builder_specification_does_not_create_app_files(tmp_path):
    result = AppBuilder(tmp_path).specification('Crie um aplicativo de tarefas com login e banco de dados')
    assert result['ok']
    assert result['specification']['screens']
    assert not list((tmp_path / 'apps').glob('**/aurora.app.json'))
