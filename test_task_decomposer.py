from pathlib import Path
from aurora.task_decomposer import TaskDecomposer


def test_decompose_builds_dependency_dag_and_reuses(tmp_path: Path):
    d = TaskDecomposer(tmp_path)
    first = d.decompose('Criar app com login, banco de dados e frontend', reuse=True)
    assert first['ok'] is True
    tasks = first['decomposition']['tasks']
    assert len(tasks) >= 5
    assert tasks[0]['depends_on'] == []
    for i in range(1, len(tasks)):
        assert tasks[i]['depends_on'] == [tasks[i-1]['id']]
    second = d.decompose('Criar app com login, banco de dados e frontend', reuse=True)
    assert second['reused'] is True


def test_next_and_mark_follow_dependencies(tmp_path: Path):
    d = TaskDecomposer(tmp_path)
    d.decompose('Criar API e testar')
    first = d.next_ready()['tasks']
    assert len(first) == 1
    tid = first[0]['id']
    assert d.mark(tid, 'done')['ok']
    second = d.next_ready()['tasks']
    assert len(second) == 1
    assert second[0]['id'] != tid


def test_invalid_mark_and_empty_request(tmp_path: Path):
    d = TaskDecomposer(tmp_path)
    assert d.decompose('')['ok'] is False
    d.decompose('Criar API')
    assert d.mark('missing', 'done')['ok'] is False
    assert d.mark(d.next_ready()['tasks'][0]['id'], 'unknown')['ok'] is False
