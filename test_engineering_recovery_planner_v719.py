from pathlib import Path
from aurora.agent import Agent


def test_recovery_planner_creates_ranked_plan(tmp_path):
    agent = Agent(tmp_path)
    result = agent.engineering_recovery_planner.plan('refactor module')
    assert result['ok'] is True
    assert result['options']
    assert result['selected'] is not None
    assert result['fingerprint']


def test_recovery_planner_requires_confirmation_for_destructive_target(tmp_path):
    agent = Agent(tmp_path)
    result = agent.engineering_recovery_planner.plan('delete database records')
    assert result['ok'] is True
    assert result['selected']['id'] == 'request_confirmation'
    assert result['guardrails']['destructive'] is True
    assert result['guardrails']['ok'] is False


def test_recovery_planner_persists_history(tmp_path):
    agent = Agent(tmp_path)
    agent.engineering_recovery_planner.plan('inspect project')
    path = Path(tmp_path) / '.aurora' / 'engineering_recovery_planner.json'
    assert path.exists()
    assert agent.engineering_recovery_planner.status()['history'] == 1
