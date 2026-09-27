from aurora.agent import Agent

def test_local_execution_runs_in_workspace(tmp_path):
    a=Agent(tmp_path)
    out=a._call('local_execution',{'action':'run','command':'python -c "print(123)"'})
    assert out['ok'] and '123' in out['stdout']

def test_local_execution_status_is_local(tmp_path):
    a=Agent(tmp_path)
    out=a._call('local_execution',{'action':'status'})
    assert out['ok'] and out['mode']=='local'
