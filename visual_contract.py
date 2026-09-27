from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class VisualContract:
    """Compare an application's rendered UI contract with its project specification."""
    def __init__(self, workspace):
        self.agent = None
        self.root = Path(workspace).resolve()
        self.state_path = self.root / '.aurora' / 'visual_contract.json'
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _app(self, app_path):
        p = (self.root / app_path if not Path(app_path).is_absolute() else Path(app_path)).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError('app fora do workspace')
        return p

    @staticmethod
    def _names(items):
        out=[]
        for x in items or []:
            if isinstance(x, str): out.append(x.lower())
            elif isinstance(x, dict):
                for k in ('id','name','title','label'):
                    if x.get(k): out.append(str(x[k]).lower()); break
        return out

    def compare(self, app_path, spec: dict[str, Any] | None = None, inspected: dict[str, Any] | None = None):
        app = self._app(app_path)
        spec = spec or {}
        if inspected is None:
            ui = json.loads((app / 'frontend' / 'ui.json').read_text(encoding='utf-8'))
            inspected = {'theme': ui.get('theme', {}), 'components': ui.get('components', [])}
        expected_components = self._names(spec.get('components'))
        actual_components = self._names(inspected.get('components'))
        expected_screens = self._names(spec.get('screens'))
        actual_labels = self._names(inspected.get('components'))
        missing_components = [x for x in expected_components if x not in actual_components and x not in actual_labels]
        missing_screens = [x for x in expected_screens if not any(x in a for a in actual_labels)]
        exp_theme = spec.get('theme') or {}
        actual_theme = inspected.get('theme') or {}
        theme_mismatches = {k:{'expected':v,'actual':actual_theme.get(k)} for k,v in exp_theme.items() if k in actual_theme and actual_theme.get(k) != v}
        checks = {
            'components_present': not missing_components,
            'screens_represented': not missing_screens,
            'theme_consistent': not theme_mismatches,
            'preview_inspectable': 'components' in inspected,
        }
        issues=[]
        if missing_components: issues.append({'type':'missing_component','items':missing_components})
        if missing_screens: issues.append({'type':'missing_screen','items':missing_screens})
        if theme_mismatches: issues.append({'type':'theme_mismatch','items':theme_mismatches})
        result={'ok':True,'app_path':str(app),'checks':checks,'issues':issues,
                'expected':{'components':expected_components,'screens':expected_screens,'theme':exp_theme},
                'actual':{'components':actual_components,'theme':actual_theme},
                'compliant':not issues}
        self.state_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result

    def correction_plan(self, comparison: dict[str, Any] | None = None):
        comparison = comparison or {}
        plan=[]
        for issue in comparison.get('issues',[]):
            typ=issue.get('type')
            if typ == 'missing_component': plan.append({'action':'implement_components','items':issue.get('items',[])})
            elif typ == 'missing_screen': plan.append({'action':'implement_screens','items':issue.get('items',[])})
            elif typ == 'theme_mismatch': plan.append({'action':'align_theme','items':issue.get('items',{})})
        return {'ok':True,'needed':bool(plan),'steps':plan,'rerun':'local_preview inspect + visual_contract compare'}


    def apply_correction(self, app_path, comparison: dict[str, Any] | None = None, *, max_steps: int = 20):
        """Apply safe contract corrections to the generated preview contract.

        This is intentionally limited to the generated ``frontend/ui.json``
        contract. It does not silently rewrite arbitrary source code. The
        resulting contract can then be re-inspected and compared.
        """
        app = self._app(app_path)
        comparison = comparison or self.status().get('last') or {}
        ui_path = app / 'frontend' / 'ui.json'
        if not ui_path.exists():
            return {'ok': False, 'error': 'preview UI não encontrado', 'applied': []}
        try:
            ui = json.loads(ui_path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return {'ok': False, 'error': f'ui.json inválido: {exc}', 'applied': []}
        components = ui.setdefault('components', [])
        existing = {str(x.get('id', x.get('name', x.get('label', '')))).lower() for x in components if isinstance(x, dict)}
        applied = []
        for issue in comparison.get('issues', [])[:max_steps]:
            typ = issue.get('type')
            if typ == 'missing_component':
                for item in issue.get('items', []):
                    key = str(item).strip()
                    if key and key.lower() not in existing:
                        components.append({'id': key.lower().replace(' ', '-'), 'label': key, 'type': 'component'})
                        existing.add(key.lower())
                        applied.append({'action':'implement_component','item':key})
            elif typ == 'theme_mismatch':
                for key, item in (issue.get('items') or {}).items():
                    if isinstance(item, dict) and 'expected' in item:
                        ui.setdefault('theme', {})[key] = item['expected']
                        applied.append({'action':'align_theme','key':key,'value':item['expected']})
        ui_path.write_text(json.dumps(ui, ensure_ascii=False, indent=2), encoding='utf-8')
        return {'ok': True, 'applied': applied, 'path': str(ui_path), 'count': len(applied)}

    def auto_correct(self, app_path, spec: dict[str, Any] | None = None, *, max_rounds: int = 3):
        """Compare, apply safe corrections, and compare again until compliant."""
        history = []
        for round_no in range(1, max(1, int(max_rounds)) + 1):
            inspected = None
            try:
                inspected = self.agent.local_preview.inspect(app_path) if hasattr(self, 'agent') else None
            except Exception:
                inspected = None
            comparison = self.compare(app_path, spec, inspected)
            history.append({'round': round_no, 'comparison': comparison})
            if comparison.get('compliant'):
                return {'ok': True, 'compliant': True, 'rounds': history}
            applied = self.apply_correction(app_path, comparison)
            history[-1]['correction'] = applied
            if not applied.get('ok') or not applied.get('count'):
                break
        final = self.compare(app_path, spec)
        return {'ok': bool(final.get('compliant')), 'compliant': bool(final.get('compliant')), 'rounds': history, 'final': final}

    def status(self):
        try: return {'ok':True,'exists':self.state_path.exists(),'last':json.loads(self.state_path.read_text(encoding='utf-8'))}
        except Exception: return {'ok':True,'exists':False,'last':None}
