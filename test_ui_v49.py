import tempfile, json
from pathlib import Path
from aurora.app_builder import AppBuilder

def build_app():
    root=Path(tempfile.mkdtemp(prefix='aurora-v49-'))
    return Path(AppBuilder(root).build('Crie uma loja com login, cadastro de produtos e banco de dados', name='Loja V49', run_tests=False)['app']['path'])

def test_ui_contract_and_components():
    app=build_app(); data=json.loads((app/'frontend/ui.json').read_text(encoding='utf-8'))
    assert 'theme' in data and 'components' in data
    assert any(c['type']=='entity-form' for c in data['components'])

def test_responsive_accessible_styles():
    app=build_app(); css=(app/'frontend/styles.css').read_text(encoding='utf-8')
    assert '@media' in css and 'focus-visible' in css and 'grid-template-columns' in css

def test_generated_app_tests_still_pass():
    import subprocess, sys
    app=build_app(); p=subprocess.run([sys.executable,'-m','pytest','-q',str(app/'tests')],cwd=app,capture_output=True,text=True)
    assert p.returncode==0, p.stdout+p.stderr
