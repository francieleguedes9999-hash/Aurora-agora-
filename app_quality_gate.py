from __future__ import annotations
import ast
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class _HTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors: list[str] = []

    def error(self, message):
        self.errors.append(message)


class AppQualityGate:
    """Deterministic structural quality checks for generated applications."""
    REQUIRED = {
        'README.md', 'aurora.app.json', 'frontend/index.html',
        'preview/index.html', 'preview/preview.json',
        'backend/main.py', 'tests/test_generated_app.py',
    }

    def inspect(self, app_path: str | Path) -> dict[str, Any]:
        root = Path(app_path).resolve()
        checks: dict[str, Any] = {}
        missing = sorted(p for p in self.REQUIRED if not (root / p).is_file())
        checks['required_files'] = {'ok': not missing, 'missing': missing}

        py_files = [p for p in root.rglob('*.py') if '__pycache__' not in p.parts]
        syntax_errors = []
        for p in py_files:
            try:
                ast.parse(p.read_text(encoding='utf-8'), filename=str(p))
            except (SyntaxError, UnicodeDecodeError) as exc:
                syntax_errors.append({'path': str(p.relative_to(root)), 'error': str(exc)})
        checks['python_syntax'] = {'ok': not syntax_errors, 'errors': syntax_errors}

        html_errors = []
        for rel in ('frontend/index.html', 'preview/index.html'):
            p = root / rel
            if not p.is_file():
                continue
            parser = _HTMLValidator()
            try:
                parser.feed(p.read_text(encoding='utf-8'))
                parser.close()
            except Exception as exc:
                parser.errors.append(str(exc))
            html_errors.append({'path': rel, 'ok': not parser.errors, 'errors': parser.errors})
        checks['html'] = {'ok': all(x['ok'] for x in html_errors), 'files': html_errors}

        preview = root / 'preview' / 'index.html'
        preview_text = preview.read_text(encoding='utf-8') if preview.is_file() else ''
        checks['interactive_preview'] = {
            'ok': bool(preview_text and '<script' in preview_text and 'button' in preview_text),
            'has_script': '<script' in preview_text,
            'has_button': 'button' in preview_text,
        }
        ok = all(bool(v.get('ok')) for v in checks.values())
        return {'ok': ok, 'app_path': str(root), 'checks': checks}
