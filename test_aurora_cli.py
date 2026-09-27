from pathlib import Path
import subprocess, sys


def test_cli_creates_app(tmp_path):
    root = Path(__file__).resolve().parents[1]
    r = subprocess.run([
        sys.executable, str(root / 'aurora_cli.py'),
        'Crie um aplicativo de tarefas com cadastro e lista',
        '--name', 'CLI App', '--workspace', str(tmp_path), '--no-tests'
    ], cwd=root, text=True, capture_output=True, timeout=30)
    assert r.returncode == 0, r.stderr
    app = tmp_path / 'apps' / 'cli-app'
    assert (app / 'frontend' / 'index.html').exists()
    assert (app / 'frontend' / 'app.js').exists()
    assert (app / 'preview' / 'index.html').exists()
