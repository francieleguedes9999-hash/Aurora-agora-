from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass
class WorkflowStep:
    id: str
    type: str = "action"
    action: str | None = None
    args: dict[str, Any] | None = None
    next: str | None = None
    on_error: str | None = None
    condition: str | None = None
    retries: int = 0
    then: str | None = None
    else_: str | None = None

    def __post_init__(self):
        self.args = dict(self.args or {})
        self.retries = max(0, int(self.retries or 0))


class WorkflowEngine:
    """Persistent, deterministic workflow runner with branches and retries.

    Actions are supplied by the host application; the engine itself never
    executes arbitrary code. This keeps workflow definitions declarative and
    lets Aurora route each action through its existing tool/sandbox layer.
    """
    VALID_TYPES = {"action", "condition", "set", "end"}

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.state_dir = self.root / ".aurora"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.state_dir / "workflows.json"
        self.runs_path = self.state_dir / "workflow_runs.json"
        self.workflows = self._load(self.path)
        self.runs = self._load(self.runs_path)

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _save(path: Path, data: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def validate(self, definition: dict[str, Any]) -> dict[str, Any]:
        errors: list[dict[str, Any]] = []
        name = str(definition.get("name", "")).strip()
        if not name:
            errors.append({"type": "missing_name"})
        raw_steps = definition.get("steps", [])
        if not isinstance(raw_steps, list) or not raw_steps:
            errors.append({"type": "missing_steps"})
            return {"ok": False, "errors": errors}
        ids = [str(x.get("id", "")) for x in raw_steps if isinstance(x, dict)]
        duplicates = sorted({x for x in ids if x and ids.count(x) > 1})
        if duplicates:
            errors.append({"type": "duplicate_step_id", "ids": duplicates})
        step_ids = set(ids)
        for raw in raw_steps:
            if not isinstance(raw, dict):
                errors.append({"type": "invalid_step", "step": raw})
                continue
            sid = str(raw.get("id", ""))
            stype = str(raw.get("type", "action"))
            if not sid:
                errors.append({"type": "missing_step_id"})
            if stype not in self.VALID_TYPES:
                errors.append({"type": "invalid_step_type", "step": sid, "value": stype})
            for key in ("next", "on_error", "then", "else"):
                target = raw.get(key)
                if target and target not in step_ids:
                    errors.append({"type": "missing_target", "step": sid, "field": key, "target": target})
            if stype == "action" and not raw.get("action"):
                errors.append({"type": "missing_action", "step": sid})
            if stype == "condition" and not raw.get("condition"):
                errors.append({"type": "missing_condition", "step": sid})
        if raw_steps and not definition.get("start"):
            definition = dict(definition)
            definition["start"] = ids[0] if ids else None
        if definition.get("start") and definition["start"] not in step_ids:
            errors.append({"type": "missing_start", "target": definition["start"]})
        return {"ok": not errors, "errors": errors}

    def create(self, definition: dict[str, Any]) -> dict[str, Any]:
        definition = dict(definition)
        definition.setdefault("id", uuid.uuid4().hex[:12])
        definition.setdefault("version", 1)
        definition.setdefault("created_at", self._now())
        definition.setdefault("start", (definition.get("steps") or [{}])[0].get("id"))
        check = self.validate(definition)
        if not check["ok"]:
            return {"ok": False, **check}
        self.workflows[definition["id"]] = definition
        self._save(self.path, self.workflows)
        return {"ok": True, "workflow": definition}

    def get(self, workflow_id: str) -> dict[str, Any]:
        workflow = self.workflows.get(workflow_id)
        return {"ok": bool(workflow), "workflow": workflow} if workflow else {"ok": False, "error": "workflow não encontrado"}

    def list(self) -> list[dict[str, Any]]:
        return list(self.workflows.values())

    def _condition(self, expression: str, context: dict[str, Any]) -> bool:
        # Small declarative predicate language: key, key == value, key != value,
        # key truthiness and dotted paths. No eval is used.
        expr = expression.strip()
        m = re.fullmatch(r"([A-Za-z_][\w.]*)\s*(==|!=)\s*(.+)", expr)
        if m:
            actual = self._get(context, m.group(1))
            expected_raw = m.group(3).strip()
            if (expected_raw.startswith('"') and expected_raw.endswith('"')) or (expected_raw.startswith("'") and expected_raw.endswith("'")):
                expected = expected_raw[1:-1]
            elif expected_raw.lower() in {"true", "false"}:
                expected = expected_raw.lower() == "true"
            elif expected_raw.lower() == "null":
                expected = None
            else:
                try: expected = float(expected_raw) if "." in expected_raw else int(expected_raw)
                except ValueError: expected = expected_raw
            return actual == expected if m.group(2) == "==" else actual != expected
        return bool(self._get(context, expr))

    @staticmethod
    def _get(context: dict[str, Any], path: str) -> Any:
        value: Any = context
        for part in path.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    @staticmethod
    def _set(context: dict[str, Any], path: str, value: Any) -> None:
        parts = path.split('.')
        target = context
        for part in parts[:-1]:
            if not isinstance(target.get(part), dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    def run(self, workflow_id: str, action: Callable[[str, dict[str, Any], dict[str, Any]], Any], context: dict[str, Any] | None = None, max_steps: int = 100) -> dict[str, Any]:
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"ok": False, "error": "workflow não encontrado"}
        run_id = uuid.uuid4().hex[:12]
        ctx = dict(context or {})
        state = {"id": run_id, "workflow_id": workflow_id, "status": "running", "started_at": self._now(), "current": workflow.get("start"), "context": ctx, "history": []}
        self.runs[run_id] = state
        self._save(self.runs_path, self.runs)
        steps = {str(s["id"]): WorkflowStep(**{k: v for k, v in {**s, "else_": s.get("else")}.items() if k != "else"}) for s in workflow.get("steps", [])}
        current = state["current"]
        visited = 0
        while current and visited < max_steps:
            visited += 1
            step = steps[current]
            try:
                if step.type == "end":
                    state["history"].append({"step": current, "status": "done"})
                    state["status"] = "completed"
                    break
                if step.type == "condition":
                    result = self._condition(step.condition or "", state["context"])
                    nxt = step.then if result else step.else_
                    state["history"].append({"step": current, "status": "condition", "result": result, "next": nxt})
                    current = nxt or step.next
                    continue
                if step.type == "set":
                    key = str(step.args.get("key", ""))
                    if not key: raise ValueError("set requer args.key")
                    self._set(state["context"], key, step.args.get("value"))
                    result = state["context"]
                else:
                    result = None
                    attempts = 0
                    while True:
                        try:
                            result = action(str(step.action), dict(step.args), state["context"])
                            break
                        except Exception as exc:
                            attempts += 1
                            if attempts > step.retries:
                                raise
                    state["context"][step.id] = result
                state["history"].append({"step": current, "status": "done", "result": result})
                current = step.next
            except Exception as exc:
                state["history"].append({"step": current, "status": "error", "error": str(exc)})
                current = step.on_error
                if not current:
                    state["status"] = "failed"
                    state["error"] = str(exc)
                    break
        else:
            if state["status"] == "running":
                state["status"] = "max_steps"
        if state["status"] == "running":
            state["status"] = "completed" if not current else "failed"
        state["current"] = current
        state["finished_at"] = self._now()
        self.runs[run_id] = state
        self._save(self.runs_path, self.runs)
        return {"ok": state["status"] == "completed", "run": state}

    def status(self, run_id: str | None = None) -> dict[str, Any]:
        if run_id:
            run = self.runs.get(run_id)
            return {"ok": bool(run), "run": run} if run else {"ok": False, "error": "execução não encontrada"}
        return {"ok": True, "runs": list(self.runs.values())[-20:]}
