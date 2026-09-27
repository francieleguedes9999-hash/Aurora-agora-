from aurora.resource_intelligence import ResourceIntelligence

def test_resource_inspect_and_workers(tmp_path):
    r=ResourceIntelligence(tmp_path)
    x=r.inspect()
    assert x['ok'] and x['cpu_count'] >= 1 and x['disk_free_bytes'] >= 0
    w=r.recommend_workers(8, [{'payload': {'resource_class': 'heavy'}}])
    assert w['ok'] and 1 <= w['recommended'] <= 8

def test_resource_check_port_and_requirements(tmp_path):
    r=ResourceIntelligence(tmp_path)
    p=r.check_port(1)
    assert p['ok']
    c=r.check({'min_disk_free_bytes': 0})
    assert c['ok'] and c['problems'] == []
