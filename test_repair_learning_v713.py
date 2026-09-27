from pathlib import Path
from aurora.repair_learning import RepairLearning

def test_patterns_generalize_successful_repairs(tmp_path: Path):
    rl = RepairLearning(tmp_path)
    rl.record('TypeError id 1234', {'kind': 'type'}, 'corrigir assinatura', 'x.py', True)
    rl.record('TypeError id 9876', {'kind': 'type'}, 'corrigir assinatura', 'y.py', True)
    patterns = rl.patterns()
    assert patterns
    assert patterns[0]['count'] == 2
    assert '<n>' in patterns[0]['pattern']

def test_contextual_returns_matches_and_guidance(tmp_path: Path):
    rl = RepairLearning(tmp_path)
    rl.record('NameError missing variable', {'kind': 'name'}, 'definir variável', 'a.py', True)
    ctx = rl.contextual('NameError missing variable', {'kind': 'name'}, 'a.py')
    assert ctx['ok'] is True
    assert ctx['matches']
    assert 'definir variável' in ctx['guidance']
