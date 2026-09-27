from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CycleReport:
    id: str
    request: str
    status: str = "running"
    phase: str = "planning"
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None
    steps: int = 0
    result: Any = None
    observations: list[dict[str, Any]] = field(default_factory=list)


class DevelopmentCycle:
    """Orquestra planejamento, contexto, pesquisa, implementação, execução,
    testes, diagnóstico e novas tentativas em um único ciclo persistente.
    """
    def __init__(self, agent: Any, max_steps: int = 12):
        self.agent = agent
        self.max_steps = max(1, int(max_steps))
        self.root = Path(agent.workspace.root)
        self.path = self.root / ".aurora" / "cycle.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self, report: CycleReport) -> None:
        self.path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _phase(observation: dict[str, Any]) -> str:
        tool = observation.get("action", {}).get("tool", "")
        if tool in {"plan", "resume_plan"}: return "planning"
        if tool in {"project_context", "list_files", "read_file", "recall"}: return "context"
        if tool == "research": return "research"
        if tool in {"write_file", "edit_file", "preview_edit", "rollback_edit"}: return "implementation"
        if tool in {"run_command", "parallel_tasks", "tasks"}: return "execution"
        if tool == "run_tests": return "testing"
        if tool == "diagnose": return "diagnosis"
        if tool in {"remember"}: return "memory"
        return "reasoning"

    def run(self, request: str, session_id: str | None = None) -> dict[str, Any]:
        from .core_loop import AgentCore
        import uuid
        report = CycleReport(uuid.uuid4().hex[:12], request)
        self._save(report)
        self.agent.planner.ensure(request)
        core = AgentCore(self.agent, max_steps=self.max_steps)
        result = core.run(request)
        report.steps = int(result.get("step", len(result.get("observations", []))))
        report.observations = result.get("observations", [])
        if report.observations:
            report.phase = self._phase(report.observations[-1])
            # Se a última alteração registrada for uma edição e os testes falharem,
            # desfazemos somente a edição mais recente, desde que o arquivo não tenha
            # sido alterado depois dela. Isso evita deixar o workspace quebrado.
            obs = report.observations[-1]
            action = obs.get("action", {})
            result_obs = obs.get("result", {})
            if action.get("tool") == "run_tests" and isinstance(result_obs, dict) and not result_obs.get("passed", result_obs.get("ok", False)):
                recent = report.observations[-2] if len(report.observations) >= 2 else None
                if recent and recent.get("action", {}).get("tool") == "edit_file":
                    try:
                        rollback = self.agent._call("rollback_edit", {})
                        obs["rollback"] = rollback
                    except Exception as exc:
                        obs["rollback"] = {"ok": False, "error": str(exc)}
        status = result.get("status", "unknown")
        report.status = status
        report.result = result.get("result")
        report.finished_at = _now()
        self._save(report)
        if session_id:
            self.agent.sessions.set_state(session_id, plan_id=(self.agent.planner.plan.id if self.agent.planner.plan else None), last_status=status)
        result["cycle_id"] = report.id
        result["phase"] = report.phase
        return result

    def resume(self, request: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        plan = self.agent.planner.resume()
        req = request or (plan.request if plan else "")
        if not req:
            return {"status": "no_active_plan"}
        return self.run(req, session_id=session_id)

    def status(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {"status": "none"}
