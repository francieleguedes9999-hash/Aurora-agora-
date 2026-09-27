import tempfile
from pathlib import Path
from aurora.versions import ProjectVersionManager

def test_snapshot_diff_and_restore_external():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)/'project'; root.mkdir(); (root/'app.py').write_text('one')
        m=ProjectVersionManager(root); a=m.snapshot('first'); vid=a['version']['id']
        (root/'app.py').write_text('two'); (root/'new.txt').write_text('new')
        diff=m.diff(vid); assert diff['ok'] and 'app.py' in diff['changed'] and 'new.txt' in diff['added']
        dest=Path(d)/'restore'; r=m.restore(vid,dest); assert r['ok']; assert (dest/'app.py').read_text()=='one'

def test_restore_workspace_requires_explicit_flag_and_removes_stale():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'a.txt').write_text('a'); m=ProjectVersionManager(root); a=m.snapshot();
        (root/'b.txt').write_text('b'); assert not m.restore(a['version']['id'])['ok']
        r=m.restore(a['version']['id'], allow_workspace=True); assert r['ok']; assert not (root/'b.txt').exists()

def test_version_path_is_safe():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)/'project'; root.mkdir(); (root/'x').write_text('x'); m=ProjectVersionManager(root); a=m.snapshot()
        bad=Path(d)/'outside'; assert m.restore(a['version']['id'], bad)['ok']
