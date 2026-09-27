import tempfile
from pathlib import Path
from aurora.agent import Agent

def test_agent_release_tool_create_and_list():
    with tempfile.TemporaryDirectory() as d:
        root=Path(d); (root/'app.py').write_text('x=1')
        a=Agent(root)
        created=a._call('releases', {'action':'create','label':'agent-release'})
        assert created['ok']
        listed=a._call('releases', {'action':'list'})
        assert listed['ok'] and len(listed['releases']) == 1
