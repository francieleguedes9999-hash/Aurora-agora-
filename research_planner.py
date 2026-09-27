from __future__ import annotations
import hashlib, json, time
from pathlib import Path
from typing import Any


class ResearchPlanner:
    """Turns research evidence into a bounded, auditable implementation plan."""
    def __init__(self, agent: Any):
        self.agent = agent
        self.path = Path(agent.workspace.root) / '.aurora' / 'research_plans.json'
        self.data = {'plans': []}
        self._load()

    def _load(self):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(value, dict): self.data.update(value)
        except (OSError, ValueError, TypeError):
            pass

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

    @staticmethod
    def _keywords(text: str) -> list[str]:
        stop = {'para','como','com','uma','que','das','dos','por','the','and','for','with','from','this','that'}
        return [w for w in ''.join(c.lower() if c.isalnum() else ' ' for c in text).split() if len(w) > 3 and w not in stop][:24]

    def build(self, request: str, context: dict[str, Any] | None = None, force: bool = False) -> dict[str, Any]:
        request = (request or '').strip()
        if not request: return {'ok': False, 'error': 'descrição vazia'}
        context = context or {}
        raw = json.dumps({'request': request, 'context': context}, sort_keys=True, ensure_ascii=False, default=str)
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()
        if not force:
            for p in reversed(self.data['plans']):
                if p.get('fingerprint') == fingerprint:
                    return {'ok': True, **p, 'reused': True}

        research = context.get('research')
        if not isinstance(research, dict):
            research = self.agent.researcher.search(request, context={'stage': 'planning'})
        sources = research.get('sources', []) if isinstance(research, dict) else []
        evidence = []
        for source in sources[:8]:
            evidence.append({
                'title': source.get('title') or source.get('url', 'fonte'),
                'url': source.get('url'),
                'excerpt': (source.get('text') or '')[:1800],
            })

        project = (context.get('project') or '')[:5000]
        keywords = self._keywords(request)
        steps = [
            {'id': 1, 'stage': 'understand', 'action': 'extrair requisitos e restrições da solicitação'},
            {'id': 2, 'stage': 'architecture', 'action': 'definir componentes, interfaces, dependências e dados necessários'},
            {'id': 3, 'stage': 'implementation', 'action': 'implementar a menor fatia funcional verificável'},
            {'id': 4, 'stage': 'testing', 'action': 'executar testes e validar comportamento contra os requisitos'},
            {'id': 5, 'stage': 'repair', 'action': 'diagnosticar falhas, corrigir e repetir a validação'},
        ]
        if evidence:
            steps[1]['evidence'] = 'usar as fontes coletadas para decidir bibliotecas, APIs e padrões; não inventar detalhes ausentes'
        else:
            steps[1]['evidence'] = 'pesquisa indisponível ou sem fontes; marcar decisões que precisem de confirmação'

        plan = {
            'fingerprint': fingerprint,
            'request': request,
            'keywords': keywords,
            'evidence': evidence,
            'project_context': project,
            'steps': steps,
            'constraints': [
                'preservar a arquitetura existente quando possível',
                'não afirmar que uma integração funciona sem executar uma validação',
                'registrar dependências e decisões técnicas',
                'preferir mudanças pequenas e reversíveis',
            ],
            'generated_at': time.time(),
            'source_count': len(evidence),
        }
        self.data['plans'].append(plan)
        self.data['plans'] = self.data['plans'][-100:]
        self._save()
        return {'ok': True, **plan, 'reused': False}

    def status(self):
        return {'ok': True, 'plans': len(self.data.get('plans', [])), 'path': str(self.path)}
