from __future__ import annotations
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .app_factory import AppFactory, AppSpec
from .app_spec import DetailedSpecBuilder


class AppDescriptionParser:
    """Converts a short natural-language request into a deterministic AppSpec.

    This is intentionally heuristic: a connected language model can produce a
    richer spec, while this parser gives Aurora a useful local fallback.
    """
    def parse(self, description: str, name: str | None = None) -> AppSpec:
        text = (description or '').strip()
        if not text:
            raise ValueError('descrição do aplicativo vazia')
        low = text.lower()
        app_name = name or self._name(low, text)
        kind = 'web'
        if any(x in low for x in ('api', 'rest api', 'backend api')):
            kind = 'api'
        elif any(x in low for x in ('mobile', 'android', 'ios', 'celular', 'aplicativo móvel')):
            kind = 'mobile'
        elif any(x in low for x in ('fullstack', 'full stack', 'frontend e backend', 'frontend + backend')):
            kind = 'fullstack'

        database = 'sqlite' if any(x in low for x in ('banco', 'database', 'sqlite', 'dados', 'cadastro')) else 'none'
        auth = any(x in low for x in ('login', 'autenticação', 'autenticacao', 'senha', 'usuário', 'usuario', 'conta'))
        frontend = 'html'
        backend = 'python'
        return AppSpec(name=app_name, kind=kind, frontend=frontend, backend=backend,
                       database=database, auth=auth, description=text)

    def _name(self, low: str, original: str) -> str:
        patterns = [
            r'(?:app|aplicativo|sistema|site|plataforma|projeto)\s+(?:de|para|do|da)?\s*([\wÀ-ÿ -]{2,50})',
        ]
        for pattern in patterns:
            m = re.search(pattern, original, re.I)
            if m:
                candidate = re.sub(r'\s+', ' ', m.group(1)).strip(' .,:;')
                # Remove trailing intent clauses while preserving a useful name.
                candidate = re.split(r'\s+(?:com|que|para|onde|usando|incluindo)\s+', candidate, maxsplit=1, flags=re.I)[0]
                if candidate:
                    return candidate.title()
        words = re.findall(r'[\wÀ-ÿ]+', original)
        return 'Aurora App' if not words else ' '.join(words[:3]).title()


class AppBuilder:
    """Builds an executable application from one natural-language description."""
    def __init__(self, workspace, test_runner=None):
        self.root = Path(workspace).resolve()
        self.factory = AppFactory(self.root)
        self.parser = AppDescriptionParser()
        self.spec_builder = DetailedSpecBuilder(self.root)
        self.test_runner = test_runner

    def specification(self, description: str, name: str | None = None) -> dict[str, Any]:
        base = asdict(self.parser.parse(description, name))
        detailed = self.spec_builder.build(description, base)
        return {'ok': True, 'specification': asdict(detailed)}

    def preview(self, description: str, name: str | None = None) -> dict[str, Any]:
        spec = self.parser.parse(description, name)
        preview = self.factory.preview(**asdict(spec))
        detailed = self.spec_builder.build(description, asdict(spec))
        return {'ok': True, 'spec': asdict(spec), 'detailed_spec': asdict(detailed), 'files': preview['files']}

    def build(self, description: str, name: str | None = None, run_tests: bool = True) -> dict[str, Any]:
        spec = self.parser.parse(description, name)
        detailed = self.spec_builder.build(description, asdict(spec))
        created = self.factory.create_from_detailed_spec(detailed)
        result: dict[str, Any] = {'ok': True, 'spec': asdict(spec), 'app': created}
        if run_tests and self.test_runner is not None:
            # TestRunner operates on the workspace root; temporarily target the
            # generated app by running pytest with its path as a command.
            app_path = Path(created['path'])
            result['tests'] = self.test_runner.run(command=f'python -m pytest -q "{app_path / "tests"}"')
            result['ok'] = bool(result['tests'].get('passed', result['tests'].get('ok', False)))
        return result
