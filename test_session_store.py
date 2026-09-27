from aurora.session_store import SessionStore

def test_session_persists_messages_and_state(tmp_path):
    s = SessionStore(tmp_path)
    sid = s.create('teste')
    s.append(sid, 'user', 'olá')
    s.append(sid, 'assistant', 'oi')
    s.set_state(sid, plan_id='p1', last_status='active')
    loaded = s.load(sid)
    assert loaded['title'] == 'teste'
    assert [m['role'] for m in loaded['messages']] == ['user', 'assistant']
    assert loaded['state']['plan_id'] == 'p1'

def test_recent_and_list(tmp_path):
    s = SessionStore(tmp_path)
    a = s.create('a'); b = s.create('b')
    for i in range(5): s.append(a, 'user', str(i))
    assert [x['content'] for x in s.recent(a, 2)] == ['3', '4']
    assert {x['id'] for x in s.list()} == {a, b}
