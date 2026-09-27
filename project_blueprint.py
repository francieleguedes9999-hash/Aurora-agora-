from __future__ import annotations
import hashlib, json, time
from .requirement_analyzer import RequirementAnalyzer
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BlueprintTask:
    id: str
    title: str
    stage: str
    depends_on: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    context: str = ''
    status: str = 'pending'


class ProjectBlueprint:
    """Builds a project-wide implementation blueprint before code execution."""
    def __init__(self, agent: Any):
        self.agent = agent
        self.path = Path(agent.workspace.root) / '.aurora' / 'project_blueprint.json'

    def build(self, request: str, research: bool = True) -> dict[str, Any]:
        request = (request or '').strip()
        if not request:
            return {'ok': False, 'error': 'descrição vazia'}
        requirements = RequirementAnalyzer().analyze(request)
        spec = self.agent.app_spec.build(request)
        decomposition = self.agent.task_decomposer.decompose(request, reuse=False, replace=True)
        raw_tasks = (decomposition.get('decomposition') or {}).get('tasks', [])
        tasks = []
        for t in raw_tasks:
            tasks.append(BlueprintTask(t['id'], t['title'], t.get('stage', 'implementation'),
                                       list(t.get('depends_on', [])), list(t.get('acceptance', [])),
                                       t.get('context_query', '')))
        # Add explicit architecture gates so implementation cannot outrun understanding.
        gates = [
            BlueprintTask('bp_spec', 'Validar contrato completo do aplicativo', 'architecture', [],
                          ['telas, componentes, entidades, endpoints e critérios definidos'], request),
            BlueprintTask('bp_research', 'Consolidar evidências técnicas', 'research', ['bp_spec'],
                          ['referências relevantes registradas'], request),
        ] if research else [BlueprintTask('bp_spec', 'Validar contrato completo do aplicativo', 'architecture', [],
                                          ['telas, componentes, entidades, endpoints e critérios definidos'], request)]
        # Insert a concrete application-build gate. This is the bridge from
        # the abstract blueprint to the real AppBuilder output. Later
        # engineering tasks operate on the generated application instead of
        # starting from an empty workspace.
        build_dep = 'bp_research' if research else 'bp_spec'
        build_task = BlueprintTask(
            'bp_build_app',
            'Construir a base executável do aplicativo a partir do contrato',
            'build',
            [build_dep],
            ['aplicativo gerado a partir do contrato detalhado'],
            request,
        )
        for gate in reversed(gates):
            for t in tasks:
                if not t.depends_on:
                    t.depends_on = [gate.id]
            tasks.insert(0, gate)
        gate_ids = {g.id for g in gates}
        for t in tasks:
            if t.id not in gate_ids and t.id != build_task.id:
                if build_task.id not in t.depends_on:
                    t.depends_on = [build_task.id] + list(t.depends_on)
        tasks.insert(len(gates), build_task)
        blueprint = {
            'id': hashlib.sha256((request + str(time.time())).encode()).hexdigest()[:16],
            'request': request,
            'created_at': time.time(),
            'requirements': requirements,
            'spec': asdict(spec) if hasattr(spec, '__dataclass_fields__') else {k: getattr(spec, k) for k in ('name','description','kind','frontend','backend','database','auth','screens','components','theme','entities','endpoints','user_flows','acceptance_criteria','assumptions') if hasattr(spec, k)},
            'research_required': bool(research),
            'tasks': [asdict(t) for t in tasks],
            'gates': ['bp_spec'] + (['bp_research'] if research else []),
            'status': 'ready',
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(blueprint, ensure_ascii=False, indent=2), encoding='utf-8')
        return {'ok': True, 'blueprint': blueprint}

    def load(self):
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def status(self):
        data = self.load()
        return {'ok': True, 'exists': data is not None, 'path': str(self.path),
                'status': data.get('status') if data else None,
                'tasks': len(data.get('tasks', [])) if data else 0}
