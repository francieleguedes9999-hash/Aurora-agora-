from aurora.planner import AdaptivePlanner

def test_planner_persists_and_resumes(tmp_path):
    p = AdaptivePlanner(tmp_path)
    plan = p.ensure('crie e teste uma API')
    assert len(plan.steps) >= 4
    assert (tmp_path / '.aurora' / 'plan.json').exists()
    p2 = AdaptivePlanner(tmp_path)
    assert p2.plan and p2.plan.id == plan.id
    assert p2.resume().status == 'active'

def test_planner_can_replace_plan(tmp_path):
    p = AdaptivePlanner(tmp_path)
    plan = p.replace('tarefa', [{'title': 'Implementar'}, {'title': 'Testar'}])
    assert [s.title for s in plan.steps] == ['Implementar', 'Testar']
    assert plan.steps[1].depends_on == [plan.steps[0].id]

def test_planner_adapts_after_failure(tmp_path):
    p = AdaptivePlanner(tmp_path)
    p.replace('tarefa', [{'title': 'Executar'}, {'title': 'Corrigir'}])
    p.observe('run_tests', {'ok': False, 'passed': False}, {'message': 'falhou'})
    assert p.plan.steps[0].status == 'blocked'
    assert 'falhou' in p.plan.steps[0].notes
    p.resume()
    assert p.plan.steps[0].status == 'pending'
