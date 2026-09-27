from pathlib import Path
from types import SimpleNamespace
from aurora.visual_contract import VisualContract

def test_visual_contract_detects_missing_items(tmp_path):
    app=tmp_path/'app'; (app/'frontend').mkdir(parents=True)
    (app/'frontend'/'ui.json').write_text('{"theme":{"mode":"dark"},"components":[{"id":"login","label":"Login","type":"button"}]}',encoding='utf-8')
    vc=VisualContract(tmp_path)
    r=vc.compare('app', {'components':[{'id':'login'},{'id':'dashboard'}], 'screens':['Dashboard'], 'theme':{'mode':'light'}})
    assert not r['compliant']
    assert any(i['type']=='missing_component' for i in r['issues'])
    assert any(i['type']=='theme_mismatch' for i in r['issues'])

def test_visual_contract_correction_plan():
    vc=VisualContract(Path('.'))
    r=vc.correction_plan({'issues':[{'type':'missing_component','items':['dashboard']}]})
    assert r['needed'] and r['steps'][0]['action']=='implement_components'
