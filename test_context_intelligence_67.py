from aurora.agent import Agent

def test_stage_packet_ranks_and_reports_freshness(tmp_path):
    (tmp_path/'auth.py').write_text('def login():\n    return True\n', encoding='utf-8')
    (tmp_path/'main.py').write_text('from auth import login\n\ndef run():\n    return login()\n', encoding='utf-8')
    a=Agent(tmp_path)
    a.context.rebuild()
    r=a.context_intelligence.stage_packet('login authentication', 'coding', limit=4)
    assert r['ok']
    assert r['stage']=='coding'
    assert r['ranked_items']
    assert all('freshness' in x and 'score' in x for x in r['ranked_items'])

def test_stage_cache_is_separate(tmp_path):
    (tmp_path/'app.py').write_text('def build(): return 1\n', encoding='utf-8')
    a=Agent(tmp_path)
    a.context.rebuild()
    x=a.context_intelligence.build('build app', stage='coding')
    y=a.context_intelligence.build('build app', stage='testing')
    assert x['fingerprint'] != y['fingerprint']
    assert x['stage']=='coding' and y['stage']=='testing'

def test_context_tool_stage_packet(tmp_path):
    a=Agent(tmp_path)
    r=a._call('context_intelligence', {'action':'stage_packet','request':'criar teste','stage':'testing'})
    assert r['ok'] and r['stage']=='testing'
