import json
import tempfile
import subprocess
import sys
from pathlib import Path
from aurora.app_builder import AppBuilder

def test_spec_entities_become_sqlite_contract():
    root = Path(tempfile.mkdtemp(prefix='aurora-v44-'))
    result = AppBuilder(root).build(
        'Crie uma loja com login, cadastro de produtos e banco de dados',
        name='Loja V44', run_tests=False,
    )
    app = Path(result['app']['path'])
    schema = (app / 'database' / 'schema.sql').read_text(encoding='utf-8')
    assert 'Product' in schema
    assert 'User' in schema
    backend = (app / 'backend' / 'main.py').read_text(encoding='utf-8')
    assert 'ENTITY_FIELDS' in backend
    assert 'def create_row' in backend

def test_generated_data_backend_tests_pass():
    root = Path(tempfile.mkdtemp(prefix='aurora-v44-test-'))
    result = AppBuilder(root).build(
        'Crie um sistema de tarefas com banco de dados',
        name='Tarefas V44', run_tests=False,
    )
    app = Path(result['app']['path'])
    proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(app / 'tests')],
                          cwd=app, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
