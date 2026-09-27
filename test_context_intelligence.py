from aurora.agent import Agent

def test_context_intelligence_combines_project_memory_and_plan(tmp_path):
    (tmp_path/'app.py').write_text('def create_user(name):\n    return name\n', encoding='utf-8')
    agent = Agent(tmp_path)
    agent.memory.remember('A autenticação usa create_user', tags=['auth'])
    agent.planner.ensure('criar usuário create_user')
    result = agent._call('context_intelligence', {'action':'build','request':'criar usuário create_user'})
    assert result['ok']
    assert 'project' in result['sections']
    assert 'memory' in result['sections']
    assert 'plan' in result['sections']
    assert 'create_user' in result['context']

def test_context_intelligence_reuses_identical_packet(tmp_path):
    agent = Agent(tmp_path)
    first = agent._call('context_intelligence', {'action':'build','request':'fazer dashboard'})
    second = agent._call('context_intelligence', {'action':'build','request':'fazer dashboard'})
    assert first['ok'] and second['ok']
    assert second['reused'] is True
    assert second['fingerprint'] == first['fingerprint']

def test_context_intelligence_budget(tmp_path):
    (tmp_path/'notes.md').write_text('dashboard auth users analytics ' * 3000, encoding='utf-8')
    agent = Agent(tmp_path)
    result = agent._call('context_intelligence', {'action':'build','request':'dashboard analytics','max_chars':700})
    assert result['ok']
    assert len(result['context']) <= 700
