from aurora.agent import Agent

def test_local_access_without_login(tmp_path):
    agent = Agent(str(tmp_path))
    status = agent._call('local_access', {})
    assert status['mode'] == 'local_owner'
    assert status['login_required'] is False
    assert agent.local_access.authorize()['authorized'] is True
    assert (tmp_path / '.aurora' / 'local_access.json').exists()
