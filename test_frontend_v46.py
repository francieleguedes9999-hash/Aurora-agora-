import json, tempfile, subprocess, sys
from pathlib import Path
from aurora.app_builder import AppBuilder

def build_app():
    root = Path(tempfile.mkdtemp(prefix='aurora-v46-'))
    result = AppBuilder(root).build('Crie uma loja com login, cadastro de produtos e banco de dados', name='Loja V46', run_tests=False)
    return Path(result['app']['path'])

def test_frontend_has_login_api_forms_loading_and_refresh():
    app = build_app()
    js = (app / 'frontend' / 'app.js').read_text(encoding='utf-8')
    html = (app / 'frontend' / 'index.html').read_text(encoding='utf-8')
    assert '/api/auth/login' in js
    assert 'fetch(' in js
    assert 'setLoading' in js
    assert 'showError' in js
    assert 'refreshAll' in js
    assert 'login-form' in html

def test_generated_backend_returns_token_and_protects_data():
    app = build_app()
    proc = subprocess.run([sys.executable, '-m', 'pytest', '-q', str(app / 'tests')], cwd=app, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
