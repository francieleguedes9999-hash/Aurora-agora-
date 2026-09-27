from __future__ import annotations
import json, time
from pathlib import Path
from typing import Any

from .releases import ReleaseManager


class ReleaseIntelligence:
    """Policy-driven bridge between Aurora Studio and ReleaseManager.

    A release is created only after the Studio cycle reports completion and its
    test stage is successful. Deployment is optional and is never attempted
    after a failed prerequisite.
    """
    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.releases = agent.releases if hasattr(agent, "releases") else ReleaseManager(self.root)
        self.state_path = self.root / ".aurora" / "release-intelligence.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self):
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {"current": None, "history": []}

    def _save(self, state):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.state_path)

    @staticmethod
    def _ok(value):
        return isinstance(value, dict) and bool(value.get("ok"))

    def status(self):
        state = self._load()
        return {"ok": True, "current": state.get("current"), "count": len(state.get("history", []))}

    def plan(self, label="release", deploy=False, verify=False):
        steps = ["studio", "quality_gate", "snapshot", "artifact", "release"]
        if deploy:
            steps.append("deploy")
        if verify:
            steps.append("verify")
        return {"ok": True, "label": label, "steps": steps, "workspace": str(self.root),
                "gates": ["studio_completed", "tests_passed", "artifact_verified"]}

    def run(self, request: str, label="release", deploy_config=None, deploy=False,
            dry_run=False, verify=False, session_id=None, max_steps=12):
        if not request or not request.strip():
            return {"ok": False, "status": "invalid_request", "error": "descrição vazia"}
        started = time.time()
        state = self._load()
        entry = {"id": f"ri-{int(started * 1000)}", "request": request.strip(),
                 "label": label, "status": "running", "started_at": started, "stages": []}
        state["current"] = entry
        self._save(state)

        studio = self.agent.studio.run(request, session_id=session_id, max_steps=max_steps)
        entry["stages"].append({"name": "studio", "ok": self._ok(studio), "result": studio})
        if not self._ok(studio):
            return self._finish(state, entry, "blocked", "studio_failed")

        tests = studio.get("artifacts", {}).get("tests")
        test_ok = self._ok(tests) if tests is not None else False
        entry["stages"].append({"name": "quality_gate", "ok": test_ok,
                                 "criteria": {"studio_completed": studio.get("status") == "completed",
                                              "tests_passed": test_ok}})
        if not test_ok:
            return self._finish(state, entry, "blocked", "tests_failed")

        release = self.releases.create(label, snapshot=True, artifact=True)
        entry["stages"].append({"name": "release", "ok": self._ok(release), "result": release})
        if not self._ok(release):
            return self._finish(state, entry, "blocked", "release_creation_failed")

        artifact_id = release["release"].get("artifact_id")
        artifact_check = self.releases.artifacts.verify(artifact_id) if artifact_id else {"ok": False}
        entry["stages"].append({"name": "artifact_verified", "ok": self._ok(artifact_check), "result": artifact_check})
        if not self._ok(artifact_check):
            return self._finish(state, entry, "blocked", "artifact_verification_failed")

        result = {"ok": True, "status": "release_ready", "release": release["release"],
                  "studio": studio, "artifact": artifact_check}
        if deploy or deploy_config:
            cfg = deploy_config or {"provider": "local", "command": "true", "environment": "development"}
            action = self.releases.deploy(release["release"]["id"], cfg, dry_run=dry_run)
            entry["stages"].append({"name": "deploy", "ok": self._ok(action), "result": action})
            if not self._ok(action):
                return self._finish(state, entry, "blocked", "deploy_failed", result)
            result["deployment"] = action
            if verify:
                checked = self.releases.verify(release["release"]["id"], cfg)
                entry["stages"].append({"name": "verify", "ok": self._ok(checked), "result": checked})
                result["verification"] = checked
                if not self._ok(checked):
                    return self._finish(state, entry, "blocked", "verification_failed", result)

        return self._finish(state, entry, "completed", None, result)

    def _finish(self, state, entry, status, reason, result=None):
        entry["status"] = status
        entry["finished_at"] = time.time()
        if reason:
            entry["reason"] = reason
        state.setdefault("history", []).append(entry)
        state["current"] = entry
        self._save(state)
        out = result or {"ok": False, "status": status, "reason": reason}
        out.update({"intelligence_id": entry["id"], "status": status, "stages": entry["stages"]})
        return out
