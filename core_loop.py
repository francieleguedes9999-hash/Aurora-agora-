from __future__ import annotations
from dataclasses import dataclass, field
import json
from typing import Any
from .diagnostics import diagnose

@dataclass
class Observation:
    step: int
    action: dict[str, Any]
    result: Any
    diagnostic: dict[str, Any] | None = None

@dataclass
class AgentCore:
    agent: Any
    max_steps: int = 12
    observations: list[Observation] = field(default_factory=list)

    def _prompt(self, request: str, step: int) -> str:
        plan = self.agent.planner.ensure(request)
        recent = [
            {"step": o.step, "action": o.action, "result": o.result, "diagnostic": o.diagnostic}
            for o in self.observations[-6:]
        ]
        return json.dumps({
            "request": request,
            "step": step,
            "max_steps": self.max_steps,
            "available_tools": ["list_files", "read_file", "write_file", "edit_file", "preview_edit", "rollback_edit", "research", "run_command", "run_tests", "diagnose", "remember", "recall", "plan", "resume_plan", "project_context", "tasks", "parallel_tasks"],
            "plan": self.agent.planner.context(),
            "project_context": self.agent.context.format(request, limit=4, max_total_chars=4500),
            "observations": recent,
            "instruction": "Escolha UMA próxima ação. Após falha de execução/teste, use diagnose antes de decidir a correção. Termine com {\"final\":...} quando a tarefa estiver concluída. Não invente resultados.",
        }, ensure_ascii=False)

    def run(self, request: str) -> dict[str, Any]:
        self.observations.clear()
        for step in range(1, self.max_steps + 1):
            raw = self.agent.model.ask(self._prompt(request, step))
            try:
                action = json.loads(raw)
            except json.JSONDecodeError:
                return {"status": "model_output_invalid", "step": step, "raw": raw, "observations": [o.__dict__ for o in self.observations]}

            if "final" in action:
                if self.agent.planner.plan:
                    self.agent.planner.plan.status = 'completed'
                    self.agent.planner._save()
                return {"status": "completed", "step": step, "result": action["final"], "observations": [o.__dict__ for o in self.observations]}

            tool = action.get("tool")
            args = action.get("args", {})
            try:
                result = self.agent._call(tool, args)
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}

            diagnostic = None
            if tool in {"run_command", "run_tests"} and isinstance(result, dict) and not result.get("ok", result.get("passed", False)):
                diagnostic = diagnose(result)

            self.observations.append(Observation(step, action, result, diagnostic))
            self.agent.planner.observe(tool, result, diagnostic)

        return {"status": "max_steps", "step": self.max_steps, "observations": [o.__dict__ for o in self.observations]}
