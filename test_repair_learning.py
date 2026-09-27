from pathlib import Path
from aurora.repair_learning import RepairLearning


def test_records_and_retrieves_successful_repairs(tmp_path: Path):
    rl = RepairLearning(tmp_path)
    rl.record('TypeError ao chamar função', {'kind': 'type', 'message': 'argumento inválido'}, 'corrigir assinatura', 'aurora/x.py', True)
    rl.record('SyntaxError em arquivo', {'kind': 'syntax'}, '', 'aurora/y.py', False)
    matches = rl.similar('TypeError ao chamar função', {'kind': 'type'}, 'aurora/x.py')
    assert matches
    assert matches[0]['success'] is True
    assert rl.status()['successful_repairs'] == 1


def test_persists_cases_and_limits_history(tmp_path: Path):
    rl = RepairLearning(tmp_path, max_cases=2)
    rl.record('a problem', {}, '', None, False)
    rl.record('b problem', {}, '', None, False)
    rl.record('c problem', {}, '', None, True)
    other = RepairLearning(tmp_path, max_cases=2)
    assert other.status()['cases'] == 2
    assert other.status()['successful_repairs'] == 1
