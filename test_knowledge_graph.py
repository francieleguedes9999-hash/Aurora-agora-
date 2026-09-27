from pathlib import Path
from aurora.knowledge_graph import KnowledgeGraph

def test_build_query_and_impact(tmp_path):
    (tmp_path/'a.py').write_text('from b import hello\ndef run():\n    return hello()\n',encoding='utf-8')
    (tmp_path/'b.py').write_text('def hello():\n    return 1\n',encoding='utf-8')
    g=KnowledgeGraph(tmp_path)
    r=g.build(); assert r['nodes'] >= 4 and r['edges'] >= 3
    q=g.query('hello'); assert any(n.get('name')=='hello' for n in q['nodes'])
    i=g.impact('b.py'); assert i['count'] >= 2

def test_graph_persists(tmp_path):
    (tmp_path/'main.py').write_text('print("x")',encoding='utf-8')
    g=KnowledgeGraph(tmp_path); g.build()
    assert g.graph()['rebuilt'] is False
    assert g.status()['nodes'] >= 1
