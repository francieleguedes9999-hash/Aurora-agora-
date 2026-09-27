from pathlib import Path
import pytest
from aurora.tools.terminal import SafeTerminal

def test_terminal_stays_in_workspace(tmp_path):
    t = SafeTerminal(tmp_path)
    out = t.run('python -c "print(123)"')
    assert out['ok'] and '123' in out['stdout']
    with pytest.raises(ValueError):
        t.run('pwd', '../')

def test_terminal_blocks_dangerous_pattern(tmp_path):
    t = SafeTerminal(tmp_path)
    with pytest.raises(PermissionError):
        t.run('rm -rf /')

def test_terminal_limits_output(tmp_path):
    t = SafeTerminal(tmp_path, max_output=100)
    out = t.run("python -c \"print(\'x\'*1000)\"")
    assert len(out['stdout']) <= 130
    assert 'truncado' in out['stdout']
