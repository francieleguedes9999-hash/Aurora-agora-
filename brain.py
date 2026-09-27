from __future__ import annotations
import json, os, re
from dataclasses import dataclass, field
from typing import Any, Callable
from .brain_memory import BrainMemory
from .brain_learning import BrainToolLearning
from .brain_meta_reasoning import MetaReasoning
from .brain_predictive_recovery import PredictiveCognitiveRecovery

@dataclass
class BrainConfig:
    provider: str = 'auto'
    max_context_chars: int = 18000
    max_history: int = 12
    response_retries: int = 2
    persist_sessions: bool = True
    max_sessions: int = 50

class CognitiveBrain:
    """Cognitive layer over Aurora's model + tools.

    It does not train a model. It provides the persistent reasoning contract:
    context assembly, structured action parsing, invalid-output recovery,
    and tool feedback for the next decision.
    """
    def __init__(self, agent: Any, model: Any = None, config: BrainConfig | None = None):
        self.agent = agent
        self.model = model or agent.model
        self.config = config or BrainConfig()
        self.history: list[dict[str, Any]] = []
        self.last_action: dict[str, Any] | None = None
        self.persistence = BrainMemory(agent.workspace.root, self.config.max_sessions) if self.config.persist_sessions else None
        self.learning = BrainToolLearning(agent.workspace.root) if self.config.persist_sessions else None
        self.meta = MetaReasoning(agent.workspace.root) if self.config.persist_sessions else None
        self.predictive_recovery = PredictiveCognitiveRecovery(agent.workspace.root, self.learning) if self.config.persist_sessions else None

    def status(self) -> dict[str, Any]:
        available = bool(getattr(self.model, 'available', lambda: False)())
        return {
            'ok': True,
            'provider': getattr(self.model, 'provider', self.config.provider),
            'model_available': available,
            'history_items': len(self.history),
            'max_context_chars': self.config.max_context_chars,
            'persistent_sessions': bool(self.persistence),
            'session_store': self.persistence.status() if self.persistence else None,
            'tool_learning': self.learning.status() if self.learning else None,
            'meta_reasoning': self.meta.status() if self.meta else None,
            'predictive_recovery': self.predictive_recovery.status() if self.predictive_recovery else None,
        }

    def _context(self, request: str, session_id: str | None = None, research: bool = False) -> dict[str, Any]:
        context = self.agent.context_intelligence.stage_packet(
            request, 'planning', session_id=session_id, research=research,
            limit=8, max_chars=self.config.max_context_chars, reuse=True
        )
        if session_id and self.persistence:
            context['brain_session'] = self.persistence.get(session_id)
        return context

    def build_prompt(self, request: str, session_id: str | None = None, research: bool = False) -> str:
        available = getattr(self.agent, 'available_tools', None)
        if callable(available):
            tools = available()
        else:
            tools = [
                'list_files','read_file','write_file','edit_file','research','run_command','run_tests',
                'diagnose','remember','recall','plan','project_context','build_app','app_factory',
                'engineering','autonomous','studio','knowledge_graph','impact','repair_learning','code_repair','regression_engineering'
            ]
        local_selection = self.agent.select_local_model_for_task(request) if hasattr(self.agent, 'select_local_model_for_task') else None
        payload = {
            'role': 'Aurora Cognitive Brain',
            'request': request,
            'session_id': session_id,
            'context': self._context(request, session_id, research=research),
            'memory': [m.__dict__ for m in self.agent.memory.recent(self.config.max_history)],
            'history': self.history[-self.config.max_history:],
            'learned_strategies': self.learning.suggest(request, 5) if self.learning else [],
            'meta_reasoning': self.meta.peek(self.history) if self.meta else None,
            'strategy_guidance': self.meta.guidance(self.history) if self.meta else None,
            'predictive_recovery': self.predictive_recovery.peek(request, self.history) if self.predictive_recovery else None,
            'predictive_guidance': self.predictive_recovery.guidance(self.predictive_recovery.peek(request, self.history)) if self.predictive_recovery else None,
            'training_material': self.agent.training_lab.context(request, limit=5, max_chars=7000) if hasattr(self.agent, 'training_lab') else '',
            'training_lab_status': self.agent.training_lab.status() if hasattr(self.agent, 'training_lab') else None,
            'local_model_status': self.agent.local_models.status() if hasattr(self.agent, 'local_models') else None,
            'local_model_selection': local_selection,
            'research_plan': self.agent.research_planner.build(request, context=self._context(request, session_id, research=True)) if research and hasattr(self.agent, 'research_planner') else None,
            'research_mode': research,
            'research_available': bool(getattr(self.agent.researcher, 'available', lambda: False)()) if hasattr(self.agent, 'researcher') else False,
            'tools': tools,
            'contract': {
                'choose_one_action': True,
                'tool_shape': {'tool': 'name', 'args': {}},
                'final_shape': {'final': 'answer'},
                'json_only': True,
                'never_invent_results': True,
                'diagnose_after_execution_failure': True,
                'change_strategy_after_repeated_failure': True,
                'app_build_guidance': 'Para criar aplicativos, prefira app_build_coordinator. Use repair_cycle após falhas; correções de código exigem patches exatos com old/new e, quando disponível, expected_sha256.',
                'local_model_guidance': 'Use o modelo local configurado quando disponível. Não faça download de modelos automaticamente; pull exige ação explícita.',
            },
        }
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def parse_action(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            # Accept fenced JSON from models that ignore the strict contract.
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.S)
            if not match:
                raise ValueError('saída do modelo não contém JSON válido')
            value = json.loads(match.group(1))
        if not isinstance(value, dict):
            raise ValueError('ação cognitiva precisa ser um objeto JSON')
        if 'final' in value:
            return {'final': str(value['final'])}
        tool = value.get('tool')
        args = value.get('args', {})
        if not isinstance(tool, str) or not tool:
            raise ValueError('ação precisa conter tool ou final')
        if not isinstance(args, dict):
            raise ValueError('args precisa ser um objeto')
        return {'tool': tool, 'args': args}

    def decide(self, request: str, session_id: str | None = None, inputs: list[dict[str, Any]] | None = None, research: bool = False) -> dict[str, Any]:
        prompt = self.build_prompt(request, session_id, research=research)
        raw = None
        last_error = None
        for attempt in range(self.config.response_retries + 1):
            if inputs is None:
                raw = self.model.ask(prompt)
            else:
                try:
                    raw = self.model.ask(prompt, inputs=inputs)
                except TypeError:
                    raw = self.model.ask(prompt)
            try:
                action = self.parse_action(raw)
                self.last_action = action
                return action
            except Exception as exc:
                last_error = str(exc)
                prompt = prompt + '\nCORREÇÃO: sua última resposta foi inválida. Retorne SOMENTE um objeto JSON com tool+args ou final. Erro: ' + last_error
        raise ValueError(last_error or 'ação inválida')

    def observe(self, action: dict[str, Any], result: Any, diagnostic: Any = None) -> None:
        item = {'action': action, 'result': result}
        if diagnostic is not None:
            item['diagnostic'] = diagnostic
        self.history.append(item)
        if len(self.history) > self.config.max_history * 2:
            self.history = self.history[-self.config.max_history * 2:]

    def run(self, request: str, session_id: str | None = None, max_steps: int | None = None, inputs: list[dict[str, Any]] | None = None, research: bool = False) -> dict[str, Any]:
        from .diagnostics import diagnose
        steps = max_steps or self.agent.max_steps
        self.history.clear()
        for step in range(1, steps + 1):
            action = self.decide(request, session_id, inputs=inputs, research=research)
            if 'final' in action:
                output = {'status': 'completed', 'step': step, 'result': action['final'], 'history': self.history}
                if session_id and self.persistence:
                    self.persistence.record(session_id, request, action['final'], self.history)
                if self.learning:
                    self.learning.observe(request, self.history, True)
                return output
            try:
                result = self.agent._call(action['tool'], action['args'])
            except Exception as exc:
                result = {'ok': False, 'error': str(exc)}
            diagnostic = None
            if action['tool'] in {'run_command', 'run_tests', 'monitor'} and isinstance(result, dict):
                failed = result.get('ok') is False or result.get('passed') is False
                if failed:
                    diagnostic = diagnose(result)
            self.observe(action, result, diagnostic)
            if self.predictive_recovery:
                self.predictive_recovery.predict(request, self.history)
        output = {'status': 'max_steps', 'step': steps, 'history': self.history}
        if session_id and self.persistence:
            self.persistence.record(session_id, request, output, self.history)
        if self.learning:
            self.learning.observe(request, self.history, False)
        return output
