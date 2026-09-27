import json
from pathlib import Path
from aurora.workflow_engine import WorkflowEngine


def make_engine(tmp_path):
    return WorkflowEngine(tmp_path)


def test_create_validate_and_persist(tmp_path):
    e = make_engine(tmp_path)
    definition = {
        'name': 'publish',
        'steps': [
            {'id': 'start', 'type': 'set', 'args': {'key': 'ready', 'value': True}, 'next': 'check'},
            {'id': 'check', 'type': 'condition', 'condition': 'ready == true', 'then': 'done', 'else': 'fail'},
            {'id': 'done', 'type': 'end'},
            {'id': 'fail', 'type': 'end'},
        ],
    }
    created = e.create(definition)
    assert created['ok']
    assert e.get(created['workflow']['id'])['ok']
    assert (Path(tmp_path) / '.aurora' / 'workflows.json').exists()


def test_branch_and_context(tmp_path):
    e = make_engine(tmp_path)
    created = e.create({'name':'branch','steps':[
        {'id':'check','type':'condition','condition':'approved == true','then':'yes','else':'no'},
        {'id':'yes','type':'set','args':{'key':'result','value':'approved'},'next':'end'},
        {'id':'no','type':'set','args':{'key':'result','value':'rejected'},'next':'end'},
        {'id':'end','type':'end'},
    ]})
    run = e.run(created['workflow']['id'], lambda *_: None, {'approved': True})
    assert run['ok']
    assert run['run']['context']['result'] == 'approved'


def test_action_retry_and_error_route(tmp_path):
    e = make_engine(tmp_path)
    created = e.create({'name':'retry','steps':[
        {'id':'call','type':'action','action':'unstable','retries':2,'next':'done','on_error':'recover'},
        {'id':'done','type':'end'},
        {'id':'recover','type':'set','args':{'key':'recovered','value':True},'next':'end'},
        {'id':'end','type':'end'},
    ]})
    attempts = {'n':0}
    def dispatch(name, args, ctx):
        attempts['n'] += 1
        if attempts['n'] < 3:
            raise RuntimeError('temporary')
        return {'ok':True}
    run = e.run(created['workflow']['id'], dispatch)
    assert run['ok']
    assert attempts['n'] == 3
    assert run['run']['context']['call'] == {'ok':True}


def test_failure_route(tmp_path):
    e = make_engine(tmp_path)
    created = e.create({'name':'fail','steps':[
        {'id':'call','type':'action','action':'boom','on_error':'recover'},
        {'id':'recover','type':'set','args':{'key':'recovered','value':True},'next':'end'},
        {'id':'end','type':'end'},
    ]})
    run = e.run(created['workflow']['id'], lambda *args: (_ for _ in ()).throw(RuntimeError('boom')))
    assert run['ok']
    assert run['run']['context']['recovered'] is True


def test_validation_catches_bad_targets(tmp_path):
    e = make_engine(tmp_path)
    result = e.validate({'name':'bad','steps':[{'id':'a','type':'action','action':'x','next':'missing'}]})
    assert not result['ok']
    assert any(x['type']=='missing_target' for x in result['errors'])
