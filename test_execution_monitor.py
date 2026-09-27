import time
from pathlib import Path
from aurora.execution_monitor import ExecutionMonitor

def test_monitor_success_and_history(tmp_path):
    m = ExecutionMonitor(tmp_path)
    r = m.run(lambda: {'ok': True, 'value': 3}, name='ok')
    assert r['ok'] and r['run']['status'] == 'completed'
    assert m.status()['runs'][-1]['name'] == 'ok'

def test_monitor_retry(tmp_path):
    m = ExecutionMonitor(tmp_path); calls = {'n': 0}
    def f():
        calls['n'] += 1
        return {'ok': calls['n'] >= 2}
    r = m.run(f, retries=1)
    assert r['ok'] and len(r['run']['attempts']) == 2

def test_monitor_timeout(tmp_path):
    m = ExecutionMonitor(tmp_path)
    r = m.run(lambda: time.sleep(0.2), timeout=0.02)
    assert not r['ok'] and r['run']['status'] == 'timeout'
