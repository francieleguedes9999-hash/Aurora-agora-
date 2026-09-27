from pathlib import Path
from aurora.tools.terminal import SafeTerminal
from aurora.tools.test_runner import TestRunner


def test_safe_terminal_runs_inside_workspace(tmp_path):
    r = SafeTerminal(tmp_path).run("python -c \"print('aurora-ok')\"")
    assert r["ok"] and "aurora-ok" in r["stdout"]


def test_terminal_rejects_escape(tmp_path):
    try:
        SafeTerminal(tmp_path)._check_cwd("../")
    except ValueError:
        return
    assert False, "escape should be rejected"


def test_test_runner(tmp_path):
    (tmp_path / "test_sample.py").write_text("def test_ok():\n    assert 2 + 2 == 4\n")
    assert TestRunner(tmp_path).run()["passed"]

def test_terminal_timeout_is_structured(tmp_path):
    from aurora.tools.terminal import SafeTerminal
    from aurora.diagnostics import diagnose
    r = SafeTerminal(tmp_path, timeout=1).run('python -c "import time; time.sleep(2)"')
    assert r['timed_out'] is True
    assert diagnose(r)['kind'] == 'timeout'
