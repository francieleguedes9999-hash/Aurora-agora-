import json,tempfile
from pathlib import Path
from aurora.app_builder import AppBuilder
from aurora.visual_editor import VisualEditor

def make_app():
    root=Path(tempfile.mkdtemp()); r=AppBuilder(root).build('Crie uma loja com produtos',name='Loja',run_tests=False); return root,Path(r['app']['path'])

def test_preview_does_not_write():
    root,a=make_app(); before=(a/'frontend/ui.json').read_text(); out=VisualEditor(root).preview(a,'menu lateral e duas colunas'); assert out['preview']; assert (a/'frontend/ui.json').read_text()==before

def test_undo_redo():
    root,a=make_app(); e=VisualEditor(root); e.apply(a,'tema escuro'); assert json.loads((a/'frontend/ui.json').read_text())['theme']['mode']=='dark'; e.undo(a); assert json.loads((a/'frontend/ui.json').read_text())['theme'].get('mode')!='dark'; e.redo(a); assert json.loads((a/'frontend/ui.json').read_text())['theme']['mode']=='dark'

def test_target_component_hide():
    root,a=make_app(); e=VisualEditor(root); e.apply(a,'adicione botão novo'); out=e.apply(a,'componente new-record-button oculte'); assert 'new-record-button=hidden' in out['changes']
