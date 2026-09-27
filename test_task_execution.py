from pathlib import Path
from aurora.task_decomposer import TaskDecomposer
from aurora.task_manager import TaskManager
from aurora.task_execution import TaskExecutionCoordinator


def test_prepare_maps_decomposition_into_persistent_tasks(tmp_path: Path):
    d = TaskDecomposer(tmp_path)
    tm = TaskManager(tmp_path)
    x = TaskExecutionCoordinator(tmp_path, d, tm)
    result = x.prepare('Criar app com login e banco de dados')
    assert result['ok']
    assert result['created_tasks']
    assert all(t['kind'] == 'engineering' for t in result['created_tasks'])


def test_execute_respects_dependencies_and_resumes(tmp_path: Path):
    d = TaskDecomposer(tmp_path)
    tm = TaskManager(tmp_path, max_workers=2)
    x = TaskExecutionCoordinator(tmp_path, d, tm)
    x.prepare('Criar API')
    seen = []
    def runner(task):
        seen.append(task.id)
        return {'ok': True, 'task': task.id}
    result = x.run(runner, max_rounds=20)
    assert result['ok'] is True
    assert result['status'] == 'completed'
    assert len(seen) >= 4
    assert x.status()['execution']['status'] == 'completed'


def test_failed_task_is_persisted(tmp_path: Path):
    d = TaskDecomposer(tmp_path)
    tm = TaskManager(tmp_path)
    x = TaskExecutionCoordinator(tmp_path, d, tm)
    x.prepare('Criar API')
    def runner(task):
        return {'ok': False, 'error': 'falhou'}
    result = x.run(runner, max_rounds=2)
    assert result['ok'] is False
    assert result['status'] == 'failed'
    assert result['execution']['failed']
