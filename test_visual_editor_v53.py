import tempfile
from pathlib import Path
from aurora.app_builder import AppBuilder
from aurora.visual_editor import VisualEditor

def make_app():
    root=Path(tempfile.mkdtemp()); r=AppBuilder(root).build('Crie uma loja com produtos',name='Loja',run_tests=False); return root,Path(r['app']['path'])

def test_inspect_component_properties():
    root,a=make_app(); e=VisualEditor(root); e.apply(a,'adicione botão novo'); out=e.inspect_component(a,'new-record-button'); assert out['ok']; assert out['editable']['style']

def test_set_structured_properties():
    root,a=make_app(); e=VisualEditor(root); e.apply(a,'adicione botão novo'); out=e.set_properties(a,'new-record-button',{'width':'180px','background':'#111','radius':12,'text':'Criar produto'}); assert out['ok']; c=out['component']; assert c['label']=='Criar produto' and c['props']['width']=='180px'

def test_preview_structured_properties_does_not_write():
    root,a=make_app(); e=VisualEditor(root); e.apply(a,'adicione botão novo'); before=(a/'frontend/ui.json').read_text(); out=e.set_properties(a,'new-record-button',{'hidden':True},preview=True); assert out['preview']; assert (a/'frontend/ui.json').read_text()==before

def test_unknown_property_rejected():
    root,a=make_app(); e=VisualEditor(root); e.apply(a,'adicione botão novo');
    try: e.set_properties(a,'new-record-button',{'onclick_code':'alert(1)'})
    except ValueError as exc: assert 'não permitida' in str(exc)
    else: assert False
