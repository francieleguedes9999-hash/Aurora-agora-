from aurora.knowledge_graph import KnowledgeGraph
from aurora.impact import ImpactPlanner

def test_impact_scopes_files_and_tests(tmp_path):
    (tmp_path/'app.py').write_text('from util import f\ndef run(): return f()\n')
    (tmp_path/'util.py').write_text('def f(): return 1\n')
    (tmp_path/'tests').mkdir()
    (tmp_path/'tests'/'test_util.py').write_text('def test_f(): pass\n')
    g=KnowledgeGraph(tmp_path); g.build()
    p=ImpactPlanner(tmp_path,g)
    r=p.analyze('util.py')
    assert r['ok'] and 'util.py' in r['files'] and 'tests/test_util.py' in r['tests']

def test_preflight_is_deterministic(tmp_path):
    (tmp_path/'main.py').write_text('print(1)\n')
    g=KnowledgeGraph(tmp_path); g.build(); p=ImpactPlanner(tmp_path,g)
    a=p.preflight('main.py'); b=p.preflight('main.py')
    assert a['fingerprint']==b['fingerprint']
