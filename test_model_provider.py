import json
import sys
from aurora.model import Model

def test_command_provider_available(tmp_path):
    m = Model(command="printf '%s' '{\"final\":\"ok\"}'", provider='command')
    assert m.available()
    assert json.loads(m.ask('x'))['final'] == 'ok'

def test_http_provider_configuration_without_call():
    m = Model(provider='openai', api_key='key', model='demo')
    assert m.available()
