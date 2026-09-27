import json, tempfile
from pathlib import Path
from aurora.app_builder import AppBuilder

def build():
    root=Path(tempfile.mkdtemp(prefix='aurora-v48-'))
    return Path(AppBuilder(root).build('Crie uma loja com banco de dados, produtos e clientes', name='Loja V48', run_tests=False)['app']['path'])

def test_relationships_and_migrations_are_generated():
    app=build()
    assert (app/'database/migrations/001_initial.sql').exists()
    assert (app/'database/migrate.py').exists()
    assert (app/'database/relationships.json').exists()

def test_backend_supports_search_sort_and_pagination():
    text=(build()/'backend/main.py').read_text(encoding='utf-8')
    assert 'parse_qs' in text and 'search' in text and 'ORDER BY' in text and 'LIMIT ? OFFSET ?' in text

def test_frontend_has_search_and_sort_controls():
    text=(build()/'frontend/app.js').read_text(encoding='utf-8')
    assert 'Buscar...' in text and 'Ordenar:' in text and 'URLSearchParams' in text
