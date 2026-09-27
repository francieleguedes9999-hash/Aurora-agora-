from pathlib import Path
import tempfile
from aurora.app_builder import AppBuilder

def test_generated_app_contains_standalone_html_preview():
    root = Path(tempfile.mkdtemp(prefix='aurora-v759-'))
    result = AppBuilder(root).build('Crie uma loja com cadastro de produtos e banco de dados', name='Loja Preview', run_tests=False)
    app = Path(result['app']['path'])
    preview = app / 'preview' / 'index.html'
    assert preview.exists()
    html = preview.read_text(encoding='utf-8')
    assert '<!doctype html>' in html.lower()
    assert 'Preview local da Aurora' in html
    assert 'Adicionar' in html
    assert (app / 'preview' / 'preview.json').exists()

def test_preview_is_self_contained_without_fetch():
    root = Path(tempfile.mkdtemp(prefix='aurora-v759-'))
    result = AppBuilder(root).build('Crie um cadastro de alunos', name='Alunos', run_tests=False)
    html = (Path(result['app']['path']) / 'preview' / 'index.html').read_text(encoding='utf-8')
    assert 'fetch(' not in html
    assert 'const ENTITIES=' in html
