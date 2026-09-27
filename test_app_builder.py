from aurora.app_builder import AppDescriptionParser, AppBuilder
from aurora.tools.test_runner import TestRunner


def test_parser_infers_fullstack_database_and_auth():
    spec = AppDescriptionParser().parse('Crie um aplicativo de loja com login e cadastro de produtos em banco de dados')
    assert spec.kind == 'web'
    assert spec.database == 'sqlite'
    assert spec.auth is True
    assert spec.name


def test_parser_detects_api_and_mobile():
    assert AppDescriptionParser().parse('Crie uma API REST de tarefas').kind == 'api'
    assert AppDescriptionParser().parse('Crie um aplicativo mobile de tarefas').kind == 'mobile'


def test_builder_creates_and_tests_app(tmp_path):
    builder = AppBuilder(tmp_path, TestRunner(tmp_path))
    result = builder.build('Crie um aplicativo de loja com login e banco de dados', name='Loja Demo')
    assert result['ok']
    assert result['tests']['passed']
    assert (tmp_path / 'apps' / 'loja-demo' / 'frontend' / 'index.html').exists()
