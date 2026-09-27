from pathlib import Path
import tempfile
from aurora.app_builder import AppBuilder
from aurora.visual_preview import VisualPreview

def make_app():
    root=Path(tempfile.mkdtemp()); r=AppBuilder(root).build('Crie uma loja com produtos',name='Loja',run_tests=False); return root,Path(r['app']['path'])

def test_inspect_components():
    root,a=make_app(); out=VisualPreview(root).inspect(a); assert 'components' in out and out['count']>=1

def test_render_contains_component_ids():
    root,a=make_app(); out=VisualPreview(root).render(a); assert '<!doctype html>' in out.lower(); assert 'data-theme=' in out

def test_write_preview_stays_in_app():
    root,a=make_app(); out=VisualPreview(root).write_preview(a); p=Path(out['path']); assert p.exists(); assert p.parent == a/'frontend'
