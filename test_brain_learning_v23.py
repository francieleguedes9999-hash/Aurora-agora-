from pathlib import Path
from aurora.brain_learning import BrainToolLearning


def test_learning_promotes_successful_sequence(tmp_path):
    l = BrainToolLearning(tmp_path)
    history = [
        {'action': {'tool': 'read_file', 'args': {}}, 'result': {'ok': True}},
        {'action': {'tool': 'edit_file', 'args': {}}, 'result': {'ok': True}},
        {'action': {'tool': 'run_tests', 'args': {}}, 'result': {'ok': True, 'passed': True}},
    ]
    l.observe('corrigir autenticação do aplicativo', history, True)
    assert l.suggest('corrigir autenticação do aplicativo')[0]['sequence'] == ['read_file', 'edit_file', 'run_tests']
    assert l.status()['strategies'] == 1


def test_failed_sequence_is_event_but_not_strategy(tmp_path):
    l = BrainToolLearning(tmp_path)
    l.observe('corrigir banco', [{'action': {'tool': 'run_tests'} , 'result': {'ok': False}}], False)
    assert l.status()['events'] == 1
    assert l.status()['strategies'] == 0


def test_persistence(tmp_path):
    l = BrainToolLearning(tmp_path)
    l.observe('criar api', [{'action': {'tool': 'write_file'}, 'result': {'ok': True}}], True)
    l2 = BrainToolLearning(tmp_path)
    assert l2.status()['strategies'] == 1
