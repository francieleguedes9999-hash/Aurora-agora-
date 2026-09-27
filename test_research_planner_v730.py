from aurora.agent import Agent
from aurora.research_planner import ResearchPlanner


def make_agent(tmp_path):
    a = Agent.__new__(Agent)
    a.workspace = type('W', (), {'root': tmp_path})()
    a.researcher = type('R', (), {'search': lambda self, q, context=None: {'available': True, 'sources': [{'title':'Docs','url':'https://example.test','text':'Use API endpoint and tests.'}]}})()
    return a


def test_research_becomes_implementation_plan(tmp_path):
    a = make_agent(tmp_path)
    p = ResearchPlanner(a)
    result = p.build('integrar uma API', context={'research': a.researcher.search('integrar uma API')})
    assert result['ok'] is True
    assert result['source_count'] == 1
    assert [s['stage'] for s in result['steps']] == ['understand','architecture','implementation','testing','repair']
    assert 'API' in result['evidence'][0]['excerpt']


def test_research_plan_is_reused(tmp_path):
    a = make_agent(tmp_path)
    p = ResearchPlanner(a)
    ctx = {'research': {'sources': [{'title':'Docs','url':'u','text':'x'}]}}
    first = p.build('teste', context=ctx)
    second = p.build('teste', context=ctx)
    assert first['reused'] is False
    assert second['reused'] is True
