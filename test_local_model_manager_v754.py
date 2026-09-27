import json
from aurora.local_model import LocalModelManager

class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps({'models': [{'name': 'llama3.2'}]}).encode()

def test_local_model_status(monkeypatch):
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **k: FakeResponse())
    m = LocalModelManager()
    s = m.status()
    assert s['ok'] is True
    assert s['model_count'] == 1
    assert s['models'][0]['name'] == 'llama3.2'

def test_pull_requires_ollama_cli(monkeypatch):
    monkeypatch.setattr('shutil.which', lambda name: None)
    result = LocalModelManager().pull('llama3.2')
    assert result['ok'] is False
    assert 'CLI' in result['error']
