from aurora.change_intelligence import ChangeIntelligence
from aurora.impact import ImpactPlanner
from aurora.knowledge_graph import KnowledgeGraph


def make_ci(tmp_path):
    (tmp_path / 'app.py').write_text('VALUE = 1\n', encoding='utf-8')
    graph = KnowledgeGraph(tmp_path)
    graph.build(force=True)
    impact = ImpactPlanner(tmp_path, graph)
    return ChangeIntelligence(tmp_path, impact, graph)


def test_compare_detects_actual_and_unexpected_changes(tmp_path):
    ci = make_ci(tmp_path)
    before = {'app.py': 'a', 'tests/test_app.py': 'b'}
    after = {'app.py': 'c', 'new.py': 'd'}
    planned = {'target': 'app.py', 'predicted_files': ['app.py']}
    result = ci.compare(before, after, planned)
    assert result['modified'] == ['app.py']
    assert result['added'] == ['new.py']
    assert result['removed'] == ['tests/test_app.py']
    assert result['unexpected'] == ['new.py', 'tests/test_app.py']
    assert result['drift'] is True


def test_execute_records_change_report(tmp_path):
    ci = make_ci(tmp_path)
    result = ci.execute('app.py', lambda: (tmp_path / 'app.py').write_text('VALUE = 2\n', encoding='utf-8'))
    assert result['ok']
    assert 'app.py' in result['comparison']['actual_files']
    assert ci.status()['history'] == 1
