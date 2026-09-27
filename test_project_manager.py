from pathlib import Path
from aurora.project_manager import ProjectManager

def test_project_manager_create_activate_remove(tmp_path):
    pm = ProjectManager(tmp_path)
    a = pm.create('Meu App', 'teste')
    b = pm.create('Outro App')
    assert Path(a.path).exists()
    assert a.active is True
    pm.activate(b.id)
    assert pm.active().id == b.id
    assert pm.summary()['count'] == 2
    pm.remove(b.id, delete_files=True)
    assert not Path(b.path).exists()
    assert pm.summary()['count'] == 1
