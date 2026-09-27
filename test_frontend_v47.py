import tempfile, subprocess, sys, json
from pathlib import Path
from aurora.app_builder import AppBuilder

def build_app():
    root=Path(tempfile.mkdtemp(prefix='aurora-v47-'))
    return Path(AppBuilder(root).build('Crie uma loja com login, cadastro de produtos e banco de dados', name='Loja V47', run_tests=False)['app']['path'])

def test_frontend_has_crud_validation_pagination_empty_state():
    app=build_app(); js=(app/'frontend/app.js').read_text(encoding='utf-8')
    assert 'method:\'PUT\'' in js and 'method:\'DELETE\'' in js
    assert 'validatePayload' in js and 'Nenhum registro encontrado' in js
    assert 'Página' in js and 'pageSize' in js

def test_backend_supports_update_delete():
    app=build_app(); text=(app/'backend/main.py').read_text(encoding='utf-8')
    assert 'def do_PUT' in text and 'def do_DELETE' in text

def test_generated_app_tests_still_pass():
    app=build_app(); proc=subprocess.run([sys.executable,'-m','pytest','-q',str(app/'tests')],cwd=app,capture_output=True,text=True)
    assert proc.returncode==0, proc.stdout+proc.stderr
