from aurora.app_factory import AppFactory

def test_factory_creates_web_fullstack(tmp_path):
    result = AppFactory(tmp_path).create(name='Minha Loja', kind='fullstack', database='sqlite', auth=True, description='Loja')
    root = tmp_path / 'apps' / 'minha-loja'
    assert result['ok']
    assert (root / 'frontend/index.html').exists()
    assert (root / 'backend/main.py').exists()
    assert (root / 'database/schema.sql').exists()
    assert (root / 'backend/auth.py').exists()
    assert (root / 'aurora.app.json').exists()

def test_factory_preview_does_not_write(tmp_path):
    result = AppFactory(tmp_path).preview(name='API', kind='api', database='none')
    assert 'backend/api.py' in result['files']
    assert not (tmp_path / 'apps').exists() or not any((tmp_path / 'apps').iterdir())
