from aurora.memory_store import LongTermMemory

def test_memory_persists_and_recalls(tmp_path):
    m=LongTermMemory(tmp_path)
    m.remember('Usar SQLite para dados locais', kind='decision', tags=['database','sqlite'])
    m.remember('O login usa JWT', kind='decision', tags=['auth'])
    got=m.search('SQLite banco', limit=5)
    assert got and 'SQLite' in got[0].text
    m2=LongTermMemory(tmp_path)
    assert len(m2.recent(5)) == 2

def test_memory_metadata(tmp_path):
    m=LongTermMemory(tmp_path)
    item=m.remember('teste', metadata={'source':'agent','iteration':3})
    assert item.metadata['iteration']==3
