from pathlib import Path
from aurora.patcher import PatchEngine
from aurora.code_repair import CodeRepair


def test_exact_patch_and_python_validation(tmp_path):
    p = tmp_path / 'app.py'
    p.write_text('value = 1\n', encoding='utf-8')
    patcher = PatchEngine(tmp_path)
    repair = CodeRepair(tmp_path, patcher)
    result = repair.repair('app.py', 'value = 1\n', 'value = 2\n')
    assert result['ok'] is True
    assert repair.inspect('app.py')['syntax_ok'] is True
    assert p.read_text(encoding='utf-8') == 'value = 2\n'


def test_invalid_patch_is_rolled_back(tmp_path):
    p = tmp_path / 'app.py'
    p.write_text('value = 1\n', encoding='utf-8')
    patcher = PatchEngine(tmp_path)
    repair = CodeRepair(tmp_path, patcher)
    result = repair.repair('app.py', 'value = 1\n', 'value = (\n')
    assert result['ok'] is False
    assert result['rolled_back']['ok'] is True
    assert p.read_text(encoding='utf-8') == 'value = 1\n'


def test_repair_plan_uses_affected_files(tmp_path):
    repair = CodeRepair(tmp_path, PatchEngine(tmp_path))
    plan = repair.plan_from_diagnosis({'affected_files': ['backend/api.py', 'frontend/ui.py']})
    assert [x['path'] for x in plan['steps']] == ['backend/api.py', 'frontend/ui.py']
    assert plan['requires_exact_patch'] is True
