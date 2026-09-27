from __future__ import annotations
import json
import re
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class PlanStep:
    id: str
    title: str
    status: str = "pending"
    depends_on: list[str] = field(default_factory=list)
    notes: str = ""

@dataclass
class Plan:
    id: str
    request: str
    status: str
    steps: list[PlanStep]
    created_at: str
    updated_at: str

class AdaptivePlanner:
    """Small persistent planner that can resume work and adapt after observations."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.path = self.root / '.aurora' / 'plan.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.plan: Plan | None = self._load()

    def _load(self) -> Plan | None:
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            steps = [PlanStep(**s) for s in data.get('steps', [])]
            return Plan(data['id'], data['request'], data['status'], steps, data['created_at'], data['updated_at'])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def _save(self) -> None:
        if not self.plan:
            return
        self.plan.updated_at = _now()
        self.path.write_text(json.dumps(asdict(self.plan), ensure_ascii=False, indent=2), encoding='utf-8')

    def _heuristic_steps(self, request: str) -> list[str]:
        text = request.lower()
        steps = ['Entender a tarefa e inspecionar o projeto']
        if any(k in text for k in ('pesquis', 'api', 'document', 'como fazer', 'biblioteca')):
            steps.append('Pesquisar informações e dependências necessárias')
        steps.append('Implementar ou editar o código')
        if any(k in text for k in ('teste', 'testar', 'funcion', 'corrig', 'bug', 'erro')) or True:
            steps.append('Executar testes ou verificações')
        steps.append('Corrigir falhas e repetir as verificações, se necessário')
        steps.append('Verificar o resultado final e encerrar')
        return steps

    def ensure(self, request: str) -> Plan:
        if self.plan and self.plan.status in {'active', 'paused'} and self.plan.request == request:
            self.plan.status = 'active'
            self._save()
            return self.plan
        names = self._heuristic_steps(request)
        steps = []
        previous = None
        for title in names:
            sid = uuid.uuid4().hex[:10]
            steps.append(PlanStep(sid, title, depends_on=[previous] if previous else []))
            previous = sid
        self.plan = Plan(uuid.uuid4().hex[:12], request, 'active', steps, _now(), _now())
        self._save()
        return self.plan

    def replace(self, request: str, steps: list[dict[str, Any]]) -> Plan:
        parsed = []
        previous = None
        for raw in steps:
            title = str(raw.get('title', '')).strip()
            if not title:
                continue
            sid = str(raw.get('id') or uuid.uuid4().hex[:10])
            deps = list(raw.get('depends_on') or ([previous] if previous else []))
            parsed.append(PlanStep(sid, title, str(raw.get('status', 'pending')), deps, str(raw.get('notes', ''))))
            previous = sid
        if not parsed:
            return self.ensure(request)
        self.plan = Plan(uuid.uuid4().hex[:12], request, 'active', parsed, _now(), _now())
        self._save()
        return self.plan

    def _next(self) -> PlanStep | None:
        if not self.plan:
            return None
        done = {s.id for s in self.plan.steps if s.status == 'done'}
        for step in self.plan.steps:
            if step.status in {'pending', 'blocked'} and all(d in done for d in step.depends_on):
                return step
        return None

    def observe(self, tool: str | None, result: Any, diagnostic: dict | None = None) -> None:
        if not self.plan:
            return
        failed = bool(isinstance(result, dict) and result.get('ok') is False)
        if tool == 'run_tests' and isinstance(result, dict):
            failed = failed or not bool(result.get('passed', result.get('ok', False)))
        if failed:
            active = next((s for s in self.plan.steps if s.status in {'pending', 'blocked'}), None)
            if active:
                active.status = 'blocked'
                active.notes = (diagnostic or {}).get('message', 'Falha observada; requer correção.')
            self._save()
            return

        keywords = {
            'list_files': ('entender', 'inspecionar'),
            'read_file': ('entender', 'inspecionar'),
            'project_context': ('entender', 'inspecionar'),
            'research': ('pesquisar',),
            'write_file': ('implementar', 'editar'),
            'run_command': ('executar', 'verificar'),
            'run_tests': ('testar', 'executar', 'verificar'),
            'diagnose': ('corrigir',),
            'remember': (), 'recall': (), 'plan': (), 'resume_plan': (),
        }
        terms = keywords.get(tool or '', ())
        target = None
        for step in self.plan.steps:
            title = step.title.lower()
            if step.status == 'pending' and any(term in title for term in terms):
                target = step
                break
        if target is None and tool in {'write_file', 'run_command', 'run_tests', 'research', 'read_file', 'list_files'}:
            target = next((s for s in self.plan.steps if s.status == 'pending'), None)
        if target:
            target.status = 'done'
            if diagnostic:
                target.notes = diagnostic.get('message', '')

        if tool in {'run_tests', 'run_command'} and not failed:
            for step in self.plan.steps:
                if step.status == 'pending' and any(k in step.title.lower() for k in ('testar', 'executar', 'verificar')):
                    step.status = 'done'
                    break
        if all(s.status == 'done' for s in self.plan.steps):
            self.plan.status = 'completed'
        else:
            self.plan.status = 'active'
        self._save()

    def complete_current(self, note: str = '') -> PlanStep | None:
        step = self._next()
        if step:
            step.status = 'done'
            if note:
                step.notes = note
            self._save()
        return step

    def resume(self) -> Plan | None:
        if self.plan:
            self.plan.status = 'active'
            for s in self.plan.steps:
                if s.status == 'blocked':
                    s.status = 'pending'
            self._save()
        return self.plan

    def context(self) -> dict[str, Any]:
        if not self.plan:
            return {'status': 'none', 'steps': []}
        return asdict(self.plan)

    def summary(self) -> str:
        if not self.plan:
            return 'Nenhum plano ativo.'
        lines = [f"Plano {self.plan.status}: {self.plan.request}"]
        for i, s in enumerate(self.plan.steps, 1):
            lines.append(f"{i}. [{s.status}] {s.title}")
        return '\n'.join(lines)
