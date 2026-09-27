import tempfile, zipfile
from pathlib import Path
from aurora.artifacts import ArtifactManager

def test_reproducible_artifact_and_verify():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'app.py').write_text('print(1)\n'); (root/'data.txt').write_text('abc')
        m=ArtifactManager(root)
        a=m.build('app'); assert a['ok']
        v=m.verify(a['artifact']['id']); assert v['ok']
        with zipfile.ZipFile(a['artifact']['package']) as z:
            assert 'app.py' in z.namelist() and 'data.txt' in z.namelist()

def test_restore_blocks_workspace_root():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'app.py').write_text('x')
        m=ArtifactManager(root); a=m.build();
        r=m.restore(a['artifact']['id'], root)
        assert not r['ok']

def test_restore_to_clean_destination():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'app.py').write_text('x')
        m=ArtifactManager(root); a=m.build()
        dest=root.parent/(root.name+'-restore')
        r=m.restore(a['artifact']['id'], dest)
        assert r['ok'] and (dest/'app.py').read_text()=='x'
