from __future__ import annotations
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AutonomousReport:
    id: str
    request: str
    status: str = "running"
    attempts: int = 0
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None
    cycles: list[dict[str, Any]] = field(default_factory=list)
    final_tests: dict[str, Any] | None = None
    final_diagnosis: dict[str, Any] | None = None


class AutonomousDeveloper:
    """Camada de alto nível que fecha o ciclo de desenvolvimento com gates.

    Ela não substitui o modelo: coordena ciclos do agente, valida o workspace
    com testes e registra o estado para retomada segura.
    """
    def __init__(self, agent: Any, max_attempts: int = 3):
        self.agent = agent
        self.max_attempts = max(1, int(max_attempts))
        self.root = Path(agent.workspace.root)
        self.path = self.root / ".aurora" / "autonomous.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self, report: AutonomousReport) -> None:
        self.path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")

    def run(self, request: str, session_id: str | None = None) -> dict[str, Any]:
        report = AutonomousReport(uuid.uuid4().hex[:12], request)
        self._save(report)
        last: dict[str, Any] = {}
        for attempt in range(1, self.max_attempts + 1):
            report.attempts = attempt
            result = self.agent.run_cycle(request, session_id=session_id)
            last = result
            report.cycles.append(result)

            tests = self.agent._call("run_tests", {})
            report.final_tests = tests
            if bool(tests.get("passed", tests.get("ok", False))):
                report.status = "completed"
                break

            report.final_diagnosis = self.agent._call("diagnose", {"result": tests})
            if attempt < self.max_attempts:
                # O próximo ciclo recebe o mesmo pedido, mas com o diagnóstico
                # persistido no histórico/memória pelo próprio agente.
                self.agent.memory.remember(
                    f"Autonomous attempt {attempt} failed tests: {report.final_diagnosis}",
                    kind="diagnosis",
                    tags=["autonomous", "repair"],
                )
            else:
                report.status = "failed"
        report.finished_at = _now()
        self._save(report)
        return {
            "status": report.status,
            "autonomous_id": report.id,
            "attempts": report.attempts,
            "result": last,
            "final_tests": report.final_tests,
            "final_diagnosis": report.final_diagnosis,
        }

    def resume(self, request: str | None = None, session_id: str | None = None) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            req = request or data.get("request", "")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            req = request or ""
        if not req:
            return {"status": "no_autonomous_task"}
        return self.run(req, session_id=session_id)

    def status(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {"status": "none"}
