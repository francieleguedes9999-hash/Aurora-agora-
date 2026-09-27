from aurora.agent import Agent

class FakeManager:
    def status(self):
        return {'ok': True, 'models': [{'name': 'llama3.2'}]}

def test_agent_initializes_local_model_manager(monkeypatch, tmp_path):
    import aurora.agent as mod
    monkeypatch.setattr(mod, 'LocalModelManager', FakeManager)
    a = Agent(workspace=str(tmp_path))
    assert a.local_models is not None
    assert hasattr(a, '_prepare_local_model')

def test_agent_selects_first_local_model_when_unconfigured(monkeypatch, tmp_path):
    import aurora.agent as mod
    monkeypatch.setattr(mod, 'LocalModelManager', FakeManager)
    a = Agent(workspace=str(tmp_path))
    assert a.model.local_model == 'llama3.2'
