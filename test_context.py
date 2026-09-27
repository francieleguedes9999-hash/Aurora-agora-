from aurora.context import ProjectContext

def test_context_indexes_and_finds_relevant_file(tmp_path):
    (tmp_path/'app.py').write_text('def create_user(name):\n    return {"name": name}\n', encoding='utf-8')
    (tmp_path/'other.py').write_text('def add(a,b):\n    return a+b\n', encoding='utf-8')
    c = ProjectContext(tmp_path)
    assert c.rebuild() == 2
    r = c.search('create user', limit=2)
    assert r and r[0].path == 'app.py'
    assert 'create_user' in r[0].text

def test_context_excludes_aurora_and_caches(tmp_path):
    (tmp_path/'.aurora').mkdir()
    (tmp_path/'.aurora'/'secret.py').write_text('secret project', encoding='utf-8')
    (tmp_path/'__pycache__').mkdir()
    (tmp_path/'__pycache__'/'x.py').write_text('cache', encoding='utf-8')
    (tmp_path/'main.py').write_text('def main(): pass', encoding='utf-8')
    c = ProjectContext(tmp_path); c.rebuild()
    paths = [x['path'] for x in c._index]
    assert paths == ['main.py']

def test_context_format_has_budget(tmp_path):
    (tmp_path/'notes.md').write_text('architecture ' * 1000, encoding='utf-8')
    c = ProjectContext(tmp_path); c.rebuild()
    out = c.format('architecture', max_total_chars=500)
    assert len(out) <= 500
