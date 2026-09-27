from __future__ import annotations
import hashlib, json, re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()[:16]


@dataclass
class DecomposedTask:
    id: str
    title: str
    kind: str = 'engineering'
    depends_on: list[str] = field(default_factory=list)
    stage: str = 'planning'
    context_query: str = ''
    acceptance: list[str] = field(default_factory=list)
    status: str = 'pending'


@dataclass
class Decomposition:
    id: str
    request: str
    fingerprint: str
    status: str
    tasks: list[DecomposedTask]
    created_at: str
    updated_at: str


class TaskDecomposer:
    """Turns a broad request into a persistent, dependency-aware engineering DAG."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.path = self.root / '.aurora' / 'decomposition.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.current: Decomposition | None = self._load()

    def _load(self) -> Decomposition | None:
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
            tasks = [DecomposedTask(**t) for t in raw.get('tasks', [])]
            return Decomposition(raw['id'], raw['request'], raw['fingerprint'], raw['status'], tasks,
                                 raw['created_at'], raw['updated_at'])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def _save(self) -> None:
        if not self.current:
            return
        self.current.updated_at = _now()
        self.path.write_text(json.dumps(asdict(self.current), ensure_ascii=False, indent=2), encoding='utf-8')

    def _has(self, text: str, *terms: str) -> bool:
        low = text.lower()
        return any(t in low for t in terms)

    def _heuristic(self, request: str) -> list[dict[str, Any]]:
        r = request.strip()
        items: list[dict[str, Any]] = []
        items.append({'title': 'Entender requisitos e estado atual do projeto', 'stage': 'planning',
                      'context_query': r, 'acceptance': ['requisitos identificados', 'estado do projeto conhecido']})
        if self._has(r, 'pesquis', 'api', 'biblioteca', 'documenta', 'integra', 'extern'):
            items.append({'title': 'Pesquisar dependências, APIs e referências necessárias', 'stage': 'research',
                          'context_query': r, 'acceptance': ['fontes relevantes registradas']})
        if self._has(r, 'banco', 'database', 'sqlite', 'postgres', 'dados', 'tabela'):
            items.append({'title': 'Projetar ou atualizar modelo de dados', 'stage': 'implementation',
                          'context_query': 'modelo de dados ' + r, 'acceptance': ['entidades e relações coerentes']})
        if self._has(r, 'login', 'autentica', 'usuário', 'usuario', 'permiss', 'auth'):
            items.append({'title': 'Implementar autenticação e autorização necessárias', 'stage': 'implementation',
                          'context_query': 'autenticação autorização ' + r, 'acceptance': ['acesso protegido conforme requisitos']})
        if self._has(r, 'tela', 'frontend', 'interface', 'ui', 'dashboard', 'página', 'pagina', 'app'):
            items.append({'title': 'Implementar interface e componentes', 'stage': 'implementation',
                          'context_query': 'frontend interface componentes ' + r, 'acceptance': ['fluxos principais representados']})
        items.append({'title': 'Implementar lógica, APIs e integrações necessárias', 'stage': 'implementation',
                      'context_query': r, 'acceptance': ['funcionalidade principal implementada']})
        items.append({'title': 'Executar testes e verificações', 'stage': 'testing',
                      'context_query': r, 'acceptance': ['testes executados', 'falhas identificadas']})
        items.append({'title': 'Corrigir falhas e repetir testes', 'stage': 'repair',
                      'context_query': r, 'acceptance': ['falhas corrigidas ou justificadas']})
        if self._has(r, 'deploy', 'public', 'produção', 'producao', 'publicar'):
            items.append({'title': 'Preparar e verificar publicação', 'stage': 'release',
                          'context_query': 'release deploy ' + r, 'acceptance': ['artefato verificado', 'publicação verificada']})
        items.append({'title': 'Verificar resultado final e registrar conclusão', 'stage': 'verification',
                      'context_query': r, 'acceptance': ['resultado final registrado']})
        return items

    def decompose(self, request: str, reuse: bool = True, replace: bool = False) -> dict[str, Any]:
        request = request.strip()
        if not request:
            return {'ok': False, 'error': 'request vazio'}
        fp = _fingerprint(request)
        if reuse and not replace and self.current and self.current.fingerprint == fp:
            return {'ok': True, 'reused': True, 'decomposition': asdict(self.current)}
        raw = self._heuristic(request)
        tasks: list[DecomposedTask] = []
        prev: str | None = None
        for i, item in enumerate(raw, 1):
            tid = f't{i:02d}_{hashlib.sha1((fp + str(i)).encode()).hexdigest()[:6]}'
            task = DecomposedTask(tid, item['title'], 'engineering', [prev] if prev else [], item['stage'], item['context_query'], item['acceptance'])
            tasks.append(task)
            prev = tid
        self.current = Decomposition(_fingerprint(request) + '-' + fp[:8], request, fp, 'ready', tasks, _now(), _now())
        self._save()
        return {'ok': True, 'reused': False, 'decomposition': asdict(self.current)}

    def next_ready(self) -> dict[str, Any]:
        if not self.current:
            return {'ok': False, 'error': 'nenhuma decomposição ativa'}
        done = {t.id for t in self.current.tasks if t.status == 'done'}
        ready = [t for t in self.current.tasks if t.status == 'pending' and all(d in done for d in t.depends_on)]
        return {'ok': True, 'tasks': [asdict(t) for t in ready]}

    def mark(self, task_id: str, status: str = 'done', note: str = '') -> dict[str, Any]:
        if not self.current:
            return {'ok': False, 'error': 'nenhuma decomposição ativa'}
        task = next((t for t in self.current.tasks if t.id == task_id), None)
        if not task:
            return {'ok': False, 'error': 'task não encontrada'}
        if status not in {'pending', 'running', 'done', 'failed', 'blocked'}:
            return {'ok': False, 'error': 'status inválido'}
        task.status = status
        if note:
            task.acceptance.append(note)
        statuses = {t.status for t in self.current.tasks}
        self.current.status = 'completed' if all(t.status == 'done' for t in self.current.tasks) else ('failed' if 'failed' in statuses else 'running')
        self._save()
        return {'ok': True, 'task': asdict(task), 'status': self.current.status}

    def status(self) -> dict[str, Any]:
        return {'ok': True, 'decomposition': asdict(self.current) if self.current else None}
