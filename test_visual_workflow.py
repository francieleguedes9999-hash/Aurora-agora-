from aurora.visual_workflow import VisualWorkflow

def test_projection_has_nodes_and_edges(tmp_path):
    g = VisualWorkflow.from_workflow({'id':'w1','name':'demo','steps':[
        {'id':'a','type':'action','action':'save','next':'c'},
        {'id':'c','type':'condition','condition':'ok','then':'yes','else':'no'},
        {'id':'yes','type':'end'}, {'id':'no','type':'end'}]})
    assert len(g['nodes']) == 4
    assert {'from':'a','to':'c','kind':'next'} in g['edges']
    assert {'from':'c','to':'yes','kind':'true'} in g['edges']

def test_save_update_and_persist(tmp_path):
    v = VisualWorkflow(tmp_path)
    g = VisualWorkflow.from_workflow({'id':'w','steps':[{'id':'a','type':'end'}]})
    assert v.save('w', g)['ok']
    assert v.update_node('w','a',{'x':120,'y':80,'label':'Fim'})['ok']
    v2 = VisualWorkflow(tmp_path)
    assert v2.get('w')['graph']['nodes'][0]['x'] == 120

def test_validation_rejects_missing_edge_target(tmp_path):
    v = VisualWorkflow(tmp_path)
    r = v.save('w', {'nodes':[{'id':'a'}], 'edges':[{'from':'a','to':'missing'}]})
    assert not r['ok']

def test_html_contains_visual_nodes(tmp_path):
    v = VisualWorkflow(tmp_path)
    g = VisualWorkflow.from_workflow({'id':'w','steps':[{'id':'a','label':'Começo','type':'set'}]})
    v.save('w', g)
    html = v.to_html('w')
    assert 'aurora-workflow-canvas' in html
    assert 'data-node-id="a"' in html
