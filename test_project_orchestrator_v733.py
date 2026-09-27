from pathlib import Path

from aurora.agent import Agent


def make_agent(tmp_path):
    a = Agent(str(tmp_path))
    return a


def test_orchestrator_prepare_creates_dependency_graph(tmp_path):
    a = make_agent(tmp_path)
    result = a._call('project_orchestrator', {'action': 'prepare', 'request': 'Criar app de notas', 'research': False})
    assert result['ok']
    assert result['state']['task_ids']
    ids = set(result['state']['task_ids'])
    for task in result['created_tasks']:
        assert task['id'] in ids
        assert all(dep in ids for dep in task['depends_on'])


def test_orchestrator_status_is_persistent(tmp_path):
    a = make_agent(tmp_path)
    a._call('project_orchestrator', {'action': 'prepare', 'request': 'Criar app simples', 'research': False})
    status = a._call('project_orchestrator', {'action': 'status'})
    assert status['ok']
    assert status['state']['status'] == 'ready'
    assert status['counts']['pending'] >= 1
