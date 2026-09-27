import json, tempfile
from pathlib import Path
from aurora.app_builder import AppBuilder
from aurora.visual_editor import VisualEditor

def app():
    root=Path(tempfile.mkdtemp(prefix='aurora-v50-'))
    r=AppBuilder(root).build('Crie uma loja com login, cadastro de produtos e banco de dados', name='Loja', run_tests=False)
    return root, Path(r['app']['path'])

def test_sidebar_and_two_columns():
    root,a=app(); out=VisualEditor(root).apply(a,'Coloque o menu lateral e deixe a tela em duas colunas')
    assert out['ok'] and out['changes']
    ui=json.loads((a/'frontend/ui.json').read_text())
    assert ui['theme']['navigation']=='sidebar' and ui['theme']['layout']=='two-column'
    assert any(c['type']=='sidebar' for c in ui['components'])
    assert 'grid-template-columns' in (a/'frontend/styles.css').read_text()

def test_new_button_and_dark_theme():
    root,a=app(); VisualEditor(root).apply(a,'Adicione um botão de novo produto e use tema escuro')
    ui=json.loads((a/'frontend/ui.json').read_text())
    assert any(c['id']=='new-record-button' for c in ui['components'])
    assert ui['theme']['mode']=='dark'

def test_rejects_outside_workspace():
    root=Path(tempfile.mkdtemp()); e=VisualEditor(root)
    try: e.apply('/tmp/not-inside','sidebar')
    except ValueError: pass
    else: raise AssertionError('expected ValueError')
