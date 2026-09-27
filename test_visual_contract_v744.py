from aurora.visual_contract import VisualContract


def test_apply_correction_updates_preview_contract(tmp_path):
    app=tmp_path/'app'; (app/'frontend').mkdir(parents=True)
    (app/'frontend'/'ui.json').write_text('{"theme":{"mode":"dark"},"components":[{"id":"login"}]}',encoding='utf-8')
    vc=VisualContract(tmp_path)
    r=vc.apply_correction('app', {'issues':[{'type':'missing_component','items':['dashboard']},{'type':'theme_mismatch','items':{'mode':{'expected':'light','actual':'dark'}}}]})
    assert r['ok'] and r['count']==2
    ui=(app/'frontend'/'ui.json').read_text(encoding='utf-8')
    assert 'dashboard' in ui and '"mode": "light"' in ui


def test_auto_correct_reaches_compliance(tmp_path):
    app=tmp_path/'app'; (app/'frontend').mkdir(parents=True)
    (app/'frontend'/'ui.json').write_text('{"theme":{"mode":"dark"},"components":[{"id":"login"}]}',encoding='utf-8')
    vc=VisualContract(tmp_path)
    r=vc.auto_correct('app', {'components':[{'id':'login'},{'id':'dashboard'}], 'theme':{'mode':'light'}})
    assert r['compliant']
