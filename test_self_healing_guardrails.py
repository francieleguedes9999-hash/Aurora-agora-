from pathlib import Path

from aurora.agent import Agent


def make_agent(tmp_path):
    return Agent(tmp_path)


def test_self_healing_executes_when_allowed(tmp_path):
    agent = make_agent(tmp_path)
    result = agent.self_healing_guardrails.run('read a small file', lambda: {'ok': True, 'value': 1})
    assert result['ok'] is True
    assert result['status'] == 'completed'
    assert result['attempts'][-1]['stage'] == 'execution'


def test_self_healing_never_bypasses_confirmation(tmp_path):
    agent = make_agent(tmp_path)
    called = []
    result = agent.self_healing_guardrails.run(
        'delete database records', lambda: called.append(True) or {'ok': True},
        alternative_runner=lambda option: {'ok': True},
        confirmed=False, max_recovery_attempts=2,
    )
    assert result['ok'] is False
    assert result['status'] == 'blocked'
    assert called == []
    assert any(a['id'] == 'request_confirmation' for a in result['alternatives'])


def test_self_healing_can_retry_with_safe_alternative(tmp_path):
    agent = make_agent(tmp_path)
    calls = []
    # Force a large-change adaptive gate, then let the alternative runner
    # simulate narrowing the target before the re-check.
    original = agent.adaptive_guardrails.evaluate
    state = {'n': 0}
    def evaluate(target, confirmed=False, base=None):
        state['n'] += 1
        if state['n'] == 1:
            return {'ok': False, 'status': 'blocked', 'gates': ['adaptive_large_change_confirmation'],
                    'reasons': ['too many files'], 'files_to_review': list(range(30))}
        return {'ok': True, 'status': 'allowed', 'gates': [], 'reasons': [], 'files_to_review': []}
    agent.adaptive_guardrails.evaluate = evaluate
    result = agent.self_healing_guardrails.run(
        'refactor module', lambda: {'ok': True},
        alternative_runner=lambda option: {'ok': True, 'option': option['id']},
        max_recovery_attempts=1,
    )
    agent.adaptive_guardrails.evaluate = original
    assert result['ok'] is True
    assert any(a['stage'] == 'recovery' for a in result['attempts'])
    assert result['status'] == 'completed'


def test_self_healing_persists_history(tmp_path):
    agent = make_agent(tmp_path)
    agent.self_healing_guardrails.run('inspect project', lambda: {'ok': True})
    path = Path(tmp_path) / '.aurora' / 'self_healing_guardrails.json'
    assert path.exists()
    assert agent.self_healing_guardrails.status()['history'] == 1
