import time
from aurora.scheduler import ParallelScheduler
from aurora.task_manager import TaskManager


def test_monitored_scheduler_completes_and_records(tmp_path):
    tm = TaskManager(tmp_path, max_workers=2)
    tm.create('a', payload={'command': 'a'})
    tm.create('b', payload={'command': 'b'})
    s = ParallelScheduler(tmp_path, tm, 2)
    r = s.run_monitored(lambda t: {'ok': True, 'id': t.id}, timeout=1)
    assert r['ok']
    assert r['run']['status'] == 'completed'
    assert len(r['run']['batches']) == 1
    assert all(x['status'] == 'done' for x in r['run']['batches'][0]['outcomes'])


def test_monitored_scheduler_timeout_marks_task_failed(tmp_path):
    tm = TaskManager(tmp_path, max_workers=1)
    slow = tm.create('slow', payload={'command': 'slow'})
    s = ParallelScheduler(tmp_path, tm, 1)
    r = s.run_monitored(lambda t: time.sleep(0.1), timeout=0.01)
    assert not r['ok']
    assert r['run']['status'] == 'failed'
    task = tm.tasks[slow.id]
    assert task.status == 'failed'
    assert 'timeout' in task.error
