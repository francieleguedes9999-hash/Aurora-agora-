from __future__ import annotations
import hashlib, json, math, os, time
from pathlib import Path
from typing import Any

STAGES = {"planning", "coding", "testing", "repair", "visual", "build", "deploy"}

class ContextIntelligence:
    """Build bounded, stage-specific project context with relevance, freshness and dependency signals."""
    def __init__(self, agent: Any, max_chars: int = 12000):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / '.aurora' / 'context_intelligence.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_chars = max_chars

    def _save(self, data: dict) -> None:
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return {'last': None, 'history': []}

    @staticmethod
    def _fingerprint(request: str, session_id: str | None, research: bool, stage: str) -> str:
        raw = json.dumps({'request': request.strip(), 'session_id': session_id, 'research': research, 'stage': stage}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _clip(self, text: str, budget: int) -> str:
        return (text or '')[:max(0, budget)]

    def _freshness(self, path: str) -> float:
        try:
            age = max(0.0, time.time() - os.path.getmtime(self.root / path))
        except OSError:
            return 0.0
        return 1.0 / (1.0 + age / 86400.0)

    def _dependencies(self, items: list[Any]) -> dict[str, set[str]]:
        paths = {getattr(i, 'path', '') for i in items}
        deps = {p: set() for p in paths}
        for item in items:
            p = getattr(item, 'path', '')
            if not p.endswith('.py'):
                continue
            try: text = (self.root / p).read_text(encoding='utf-8', errors='ignore')
            except OSError: continue
            for candidate in paths:
                stem = Path(candidate).stem
                if stem and stem != Path(p).stem and (f'from {stem} ' in text or f'import {stem}' in text):
                    deps[p].add(candidate)
        return deps

    def _rank_project(self, request: str, limit: int) -> list[Any]:
        items = self.agent.context.search(request, limit=max(limit * 3, 12), max_chars=2200)
        deps = self._dependencies(items)
        scored = []
        for item in items:
            score = float(item.score)
            fresh = self._freshness(item.path)
            score += 1.5 * fresh
            score += 0.75 * len(deps.get(item.path, set()))
            scored.append((score, item, fresh, sorted(deps.get(item.path, set()))))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:limit]

    def _stage_hint(self, stage: str) -> str:
        return {
            'planning': 'spec requisitos arquitetura plano',
            'coding': 'implementação código função classe componente endpoint',
            'testing': 'teste test assert fixture integração',
            'repair': 'erro exception traceback diagnóstico correção',
            'visual': 'frontend ui componente layout estilo fluxo',
            'build': 'build pacote manifesto dependência configuração',
            'deploy': 'deploy produção configuração ambiente health rollback',
        }.get(stage, '')

    def build(self, request: str, session_id: str | None = None, research: bool = False,
              limit: int = 6, max_chars: int | None = None, reuse: bool = True,
              stage: str = 'planning') -> dict[str, Any]:
        request = (request or '').strip()
        if not request:
            return {'ok': False, 'error': 'descrição vazia'}
        stage = stage if stage in STAGES else 'planning'
        budget = max_chars or self.max_chars
        fp = self._fingerprint(request, session_id, research, stage)
        state = self._load()
        last = state.get('last') or {}
        if reuse and last.get('fingerprint') == fp:
            cached = state['last']
            return {'ok': True, **cached, 'reused': True}

        scored = self._rank_project(request + ' ' + self._stage_hint(stage), limit)
        project_context = ''
        ranked_items = []
        for score, item, fresh, deps in scored:
            ranked_items.append({'path': item.path, 'score': round(score, 3), 'freshness': round(fresh, 3), 'dependencies': deps})
            project_context += f"FILE: {item.path}\n{item.text}\n\n---\n\n"
        project_context = project_context[:max(1800, budget // 2)]

        sections: list[tuple[str, str]] = []
        if project_context: sections.append(('project', project_context))
        memories = self.agent.memory.search(request, limit=8)
        if memories:
            sections.append(('memory', '\n'.join(f"- [{m.kind}] {m.text}" for m in memories)))
        if session_id:
            try: messages = self.agent.sessions.recent(session_id, limit=8)
            except (KeyError, ValueError): messages = []
            if messages:
                sections.append(('session', '\n'.join(f"{m.get('role','unknown')}: {m.get('content','')}" for m in messages)))
        plan = self.agent.planner.context()
        if plan.get('status') not in {None, 'none'}:
            steps = '\n'.join(f"- [{s.get('status')}] {s.get('title')}" for s in plan.get('steps', []))
            sections.append(('plan', f"Plano: {plan.get('request','')}\n{steps}"))

        research_result = None
        if research:
            research_result = self.agent.researcher.search(request, context={'project': project_context[:3000], 'stage': stage})
            sources = research_result.get('sources', []) if isinstance(research_result, dict) else []
            if sources:
                sections.append(('research', '\n'.join(f"- {s.get('title', s.get('url',''))}: {s.get('text','')[:1200]}" for s in sources[:5])))

        remaining = budget
        blocks, used = [], []
        for kind, text in sections:
            if remaining <= 0: break
            block = f"## {kind}\n{self._clip(text, remaining)}"
            if len(block) > remaining: block = block[:remaining]
            blocks.append(block); used.append(kind); remaining -= len(block) + 2
        packet = '\n\n'.join(blocks)
        result = {'fingerprint': fp, 'request': request, 'stage': stage, 'session_id': session_id,
                  'reused': False, 'sections': used, 'ranked_items': ranked_items,
                  'context': packet, 'research': research_result, 'generated_at': time.time(), 'char_count': len(packet)}
        history = state.get('history', [])
        history.append({'fingerprint': fp, 'request': request, 'stage': stage, 'ranked_items': ranked_items,
                        'generated_at': result['generated_at'], 'char_count': len(packet)})
        self._save({'last': result, 'history': history[-30:]})
        return {'ok': True, **result}

    def stage_packet(self, request: str, stage: str, **kwargs) -> dict[str, Any]:
        return self.build(request, stage=stage, **kwargs)

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {'ok': True, 'last': state.get('last'), 'history_count': len(state.get('history', []))}
