import json
from aurora.model import Model

class FakeResponse:
    status = 200
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return json.dumps(self.payload).encode()

def test_local_ollama_status_without_external_key(monkeypatch):
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **k: FakeResponse({'models': []}))
    m = Model(provider='ollama', model='llama3.2')
    s = m.status()
    assert s['local']['runtime'] == 'ollama'
    assert s['local']['configured'] is True
    assert s['local']['reachable'] is True
    assert s['available'] is True

def test_local_ollama_ask(monkeypatch):
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **k: FakeResponse({'response': '{"final":"ok"}'}))
    m = Model(provider='ollama', model='llama3.2')
    assert json.loads(m.ask('teste'))['final'] == 'ok'
