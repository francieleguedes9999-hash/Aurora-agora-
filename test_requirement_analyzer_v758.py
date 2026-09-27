from aurora.requirement_analyzer import RequirementAnalyzer
from aurora.project_blueprint import ProjectBlueprint


def test_analyzer_extracts_features_entities_and_ambiguities():
    r = RequirementAnalyzer().analyze(
        'Crie um aplicativo de loja com login, cadastro de produtos, pagamento Pix e notificações por email'
    )
    assert r['ok']
    ids = {x['id'] for x in r['features']}
    assert {'authentication', 'payments', 'notifications'} <= ids
    assert 'Produto' in r['entities']
    assert r['ambiguities']
    assert r['completeness']['level'] in {'medium', 'high'}


def test_blueprint_persists_requirement_analysis(tmp_path):
    class A: pass
    a=A(); a.workspace=type('W',(),{'root':str(tmp_path)})();
    from aurora.app_spec import DetailedSpecBuilder
    a.app_spec=DetailedSpecBuilder(tmp_path)
    a.task_decomposer=type('D',(),{'decompose':lambda self,*args,**kwargs:{'decomposition':{'tasks':[]}}})()
    result=ProjectBlueprint(a).build('Crie um aplicativo de tarefas com login')
    assert result['ok']
    req=result['blueprint']['requirements']
    assert req['ok'] and req['features']
