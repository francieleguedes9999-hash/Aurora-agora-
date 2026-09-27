from __future__ import annotations
from typing import Any

from .app_quality_gate import AppQualityGate


class AppBuildCoordinator:
    """Coordinates build -> validate -> diagnose -> safe repair -> revalidate."""
    def __init__(self, agent):
        self.agent = agent
        self.last: dict[str, Any] | None = None
        self.quality_gate = AppQualityGate()

    def _validate(self, result: dict[str, Any]) -> dict[str, Any]:
        app = result.get('app') or {}
        app_path = app.get('path')
        validation = {
            'ok': bool(result.get('ok')),
            'tests': result.get('tests'),
        }
        if validation['tests'] and not validation['tests'].get('ok', validation['tests'].get('passed', True)):
            validation['diagnosis'] = self.agent._call('diagnose', {'result': validation['tests']})
        if app_path:
            validation['quality_gate'] = self.quality_gate.inspect(app_path)
            validation['preview'] = self.agent.local_preview.build(app_path)
            validation['inspection'] = self.agent.local_preview.inspect(app_path)
            spec = result.get('spec') or {}
            comparison = self.agent.visual_contract.compare(app_path, spec, validation['inspection'])
            validation['visual_contract'] = comparison
            validation['ok'] = bool(validation['ok'] and validation['quality_gate'].get('ok', True) and comparison.get('ok', True))
        return validation

    def build_and_validate(self, description: str, name: str | None = None, run_tests: bool = True) -> dict[str, Any]:
        result = self.agent.app_builder.build(description, name, run_tests=run_tests)
        validation = self._validate(result)
        self.last = {'ok': validation['ok'], 'app': result.get('app') or {}, 'validation': validation}
        return self.last

    def repair_cycle(self, description: str, name: str | None = None, run_tests: bool = True,
                     patches: list[dict[str, Any]] | None = None, max_attempts: int = 3,
                     app_path: str | None = None) -> dict[str, Any]:
        """Run a bounded correction cycle. Patches must be exact-content, hash-guarded edits."""
        attempts = max(1, min(int(max_attempts), 5))
        history: list[dict[str, Any]] = []
        if app_path:
            app = {'path': app_path, 'name': name or app_path}
            built = {'ok': True, 'app': app, 'spec': {}}
            validation = {'ok': True}
            if run_tests:
                tests = self.agent.test_runner.run(f'python -m pytest -q "{app_path}/tests"')
                validation = {'ok': bool(tests.get('ok', tests.get('passed', False))), 'tests': tests}
                if not validation['ok']:
                    validation['diagnosis'] = self.agent._call('diagnose', {'result': tests})
            validation['quality_gate'] = self.quality_gate.inspect(app_path)
            validation['preview'] = self.agent.local_preview.build(app_path)
            validation['inspection'] = self.agent.local_preview.inspect(app_path)
            validation['visual_contract'] = self.agent.visual_contract.compare(app_path, {}, validation['inspection'])
            validation['ok'] = bool(validation['ok'] and validation['visual_contract'].get('ok', True))
        else:
            built = self.agent.app_builder.build(description, name, run_tests=run_tests)
            app = built.get('app') or {}
            validation = self._validate(built)
        history.append({'stage': 'build', 'ok': validation['ok'], 'validation': validation})

        if validation['ok'] and not patches:
            self.last = {'ok': True, 'app': app, 'attempts': 1, 'history': history, 'status': 'completed'}
            return self.last

        diagnosis = validation.get('diagnosis') or self.agent._call('diagnose', {'result': validation.get('tests') or validation})
        repair_plan = self.agent.code_repair.plan_from_diagnosis(diagnosis)
        history.append({'stage': 'diagnosis', 'ok': bool(diagnosis.get('ok') is not True), 'diagnosis': diagnosis, 'repair_plan': repair_plan})

        if not patches:
            self.last = {
                'ok': False, 'app': app, 'attempts': 1, 'status': 'needs_repair',
                'history': history, 'diagnosis': diagnosis, 'repair_plan': repair_plan,
                'requires_exact_patch': True,
            }
            return self.last

        for attempt in range(1, attempts + 1):
            applied = []
            patch_failed = None
            for patch in patches:
                try:
                    repaired = self.agent.code_repair.repair(
                        patch['path'], patch.get('old', ''), patch.get('new', ''),
                        patch.get('expected_sha256'), validate=True,
                    )
                    applied.append(repaired)
                    if not repaired.get('ok'):
                        patch_failed = repaired
                        break
                except Exception as exc:
                    patch_failed = {'ok': False, 'error': str(exc), 'path': patch.get('path')}
                    break
            history.append({'stage': f'repair_{attempt}', 'ok': patch_failed is None and all(x.get('ok') for x in applied), 'patches': applied, 'error': patch_failed})
            if patch_failed:
                break

            if app.get('path'):
                tests = self.agent.test_runner.run(f'python -m pytest -q "{app["path"]}/tests"')
                current = {'ok': tests.get('ok', tests.get('passed', False)), 'tests': tests}
                if not current['ok']:
                    current['diagnosis'] = self.agent._call('diagnose', {'result': tests})
                current['preview'] = self.agent.local_preview.build(app['path'])
                current['inspection'] = self.agent.local_preview.inspect(app['path'])
                spec = built.get('spec') or {}
                current['visual_contract'] = self.agent.visual_contract.compare(app['path'], spec, current['inspection'])
                current['ok'] = bool(current['ok'] and current['visual_contract'].get('ok', True))
            else:
                current = {'ok': False, 'error': 'app sem caminho'}
            history.append({'stage': f'revalidate_{attempt}', **current})
            if current['ok']:
                learned = None
                if hasattr(self.agent, 'repair_learning'):
                    learned = self.agent.repair_learning.record(
                        failure=description, diagnosis=diagnosis, repair=patches,
                        target=diagnosis.get('file') if isinstance(diagnosis, dict) else None,
                        success=True, metadata={'attempt': attempt, 'app': app.get('path')},
                    )
                self.last = {'ok': True, 'app': app, 'attempts': attempt + 1, 'status': 'completed', 'history': history, 'learning': learned}
                return self.last
            diagnosis = current.get('diagnosis') or self.agent._call('diagnose', {'result': current.get('tests') or current})
            history.append({'stage': f'diagnosis_{attempt}', 'ok': False, 'diagnosis': diagnosis})

        self.last = {'ok': False, 'app': app, 'attempts': len(history), 'status': 'failed', 'history': history, 'diagnosis': diagnosis}
        return self.last

    def create_app(self, description: str, name: str | None = None,
                   research: bool = False, run_tests: bool = True) -> dict[str, Any]:
        """Run the focused end-to-end app creation pipeline.

        The pipeline creates a persistent blueprint first, then builds and
        validates the generated application. Research is optional so local
        app generation remains deterministic and does not require network
        access.
        """
        description = (description or '').strip()
        if not description:
            return {'ok': False, 'status': 'invalid_request', 'error': 'descrição do aplicativo vazia'}

        blueprint_result = self.agent.project_blueprint.build(description, research=research)
        if not blueprint_result.get('ok'):
            self.last = {'ok': False, 'status': 'blueprint_failed', 'blueprint': blueprint_result}
            return self.last

        build_result = self.build_and_validate(description, name=name, run_tests=run_tests)
        result = {
            'ok': bool(build_result.get('ok')),
            'status': 'completed' if build_result.get('ok') else 'needs_repair',
            'blueprint': blueprint_result.get('blueprint'),
            'app': build_result.get('app'),
            'validation': build_result.get('validation'),
        }
        self.last = result
        return result

    def status(self) -> dict[str, Any]:
        return {'ok': True, 'last': self.last}
