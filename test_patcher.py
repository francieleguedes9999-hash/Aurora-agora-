from aurora.patcher import PatchEngine

def test_preview_and_apply(tmp_path):
    p = tmp_path/'a.txt'; p.write_text('hello\n', encoding='utf-8')
    e = PatchEngine(tmp_path)
    old='hello\n'; new='hello world\n'
    preview=e.preview('a.txt', old, new)
    assert '+hello world' in preview['diff']
    out=e.apply('a.txt', old, new, preview['before_sha256'])
    assert out['ok'] and p.read_text() == new

def test_rollback(tmp_path):
    p=tmp_path/'a.txt'; p.write_text('a\n', encoding='utf-8')
    e=PatchEngine(tmp_path); e.apply('a.txt','a\n','b\n')
    out=e.rollback_last()
    assert out['ok'] and p.read_text() == 'a\n'

def test_stale_edit_is_rejected(tmp_path):
    p=tmp_path/'a.txt'; p.write_text('current\n', encoding='utf-8')
    e=PatchEngine(tmp_path)
    try: e.apply('a.txt','old\n','new\n')
    except ValueError as exc: assert 'não corresponde' in str(exc)
    else: assert False
