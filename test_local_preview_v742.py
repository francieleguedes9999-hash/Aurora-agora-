from pathlib import Path
from aurora.local_preview import LocalPreview
from aurora.local_execution import LocalExecutionRuntime

def make_app(tmp_path):
    app=tmp_path/'demo'; (app/'frontend').mkdir(parents=True)
    (app/'frontend'/'ui.json').write_text('{"theme":{"mode":"dark","layout":"single"},"components":[{"id":"title","type":"text","label":"Olá"},{"id":"go","type":"button","label":"Entrar"}]}',encoding='utf-8')
    return app

def test_build_and_inspect_preview(tmp_path):
    app=make_app(tmp_path); ex=LocalExecutionRuntime(tmp_path); p=LocalPreview(tmp_path, ex)
    built=p.build('demo'); assert built['ok']; assert Path(built['path']).exists()
    info=p.inspect('demo'); assert info['count']==2; assert info['components'][1]['id']=='go'

def test_serve_and_stop_local_preview(tmp_path):
    app=make_app(tmp_path); ex=LocalExecutionRuntime(tmp_path); p=LocalPreview(tmp_path, ex)
    result=p.serve('demo', name='test-preview')
    assert result['ok']; assert result['url'].startswith('http://127.0.0.1:')
    stopped=p.stop('test-preview'); assert stopped['ok']
