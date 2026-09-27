from aurora.brain_meta_reasoning import MetaReasoning


def test_meta_reasoning_switches_after_repeated_failure(tmp_path):
    meta = MetaReasoning(tmp_path)
    history = [
        {'action': {'tool': 'run_tests'}, 'result': {'passed': False}},
        {'action': {'tool': 'run_tests'}, 'result': {'passed': False}},
    ]
    result = meta.evaluate(history)
    assert result['mode'] == 'switch'
    assert result['recent_failures'] == 2
    assert meta.status()['strategy_switches'] == 1


def test_meta_reasoning_continue_after_success(tmp_path):
    meta = MetaReasoning(tmp_path)
    result = meta.evaluate([{'action': {'tool': 'read_file'}, 'result': {'ok': True}}])
    assert result['mode'] == 'continue'
