from aurora.agent import Agent

def test_agent_projects_tool(tmp_path):
    a = Agent(tmp_path)
    result = a._call('projects', {'action':'create','name':'Demo'})
    assert result['ok'] and result['project']['name'] == 'Demo'
    listed = a._call('projects', {'action':'list'})
    assert listed['count'] == 1
