from aurora.scheduler import ParallelScheduler
from aurora.task_manager import TaskManager

def test_priority_and_resource_lock(tmp_path):
    tm = TaskManager(tmp_path, max_workers=3)
    tm.create('low', payload={'priority': 1, 'resources':['db']}, task_id='a')
    tm.create('high', payload={'priority': 9, 'resources':['db']}, task_id='b')
    tm.create('independent', payload={'priority': 2, 'resources':['ui']}, task_id='c')
    s = ParallelScheduler(tmp_path, tm, 3)
    p = s.plan()
    ids = [x['id'] for x in p['selected']]
    assert 'b' in ids and 'c' in ids and 'a' not in ids

def test_parallel_scheduler_runs_independent(tmp_path):
    tm = TaskManager(tmp_path, max_workers=2)
    tm.create('a', payload={'resources':['a']}, task_id='a')
    tm.create('b', payload={'resources':['b']}, task_id='b')
    tm.create('c', depends_on=['a','b'], task_id='c')
    s = ParallelScheduler(tmp_path, tm, 2)
    out = s.run(lambda t: {'ok': True, 'id': t.id}, max_rounds=5)
    assert out['ok']
    assert [tm.tasks[x].status for x in ['a','b','c']] == ['done','done','done']
