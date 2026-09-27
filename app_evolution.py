from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .diagnostics import diagnose


class AppEvolution:
    """Keeps generated applications evolving as coordinated modules.

    This layer does not pretend to modify code by itself. It creates a concrete
    module plan from the generated contract, records the target files, and
    provides focused engineering prompts for each module.
    """

    MODULES = (
        ("frontend", "Evoluir interface, telas e componentes", "frontend"),
        ("backend", "Evoluir lógica, serviços e endpoints", "backend"),
        ("data", "Evoluir banco, entidades e migrações", "database"),
        ("integration", "Evoluir integrações e fluxos entre módulos", "integration"),
        ("quality", "Validar integração completa e critérios de aceitação", "quality"),
    )

    def __init__(self, agent: Any):
        self.agent = agent
        self.root = Path(agent.workspace.root).resolve()
        self.path = self.root / ".aurora" / "app_evolution.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _save(self, state: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def _load(self) -> dict[str, Any] | None:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _app_path(self, spec: dict[str, Any]) -> Path:
        name = spec.get("name", "aurora-app")
        slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
        return self.root / "apps" / (slug or "aurora-app")

    def inspect(self, app_path: str | Path) -> dict[str, Any]:
        path = Path(app_path).resolve()
        files = []
        if path.exists():
            files = sorted(str(p.relative_to(path)) for p in path.rglob("*") if p.is_file())
        contract = {}
        contract_path = path / "aurora.contract.json"
        if contract_path.exists():
            try:
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                contract = {}
        return {
            "path": str(path),
            "exists": path.exists(),
            "file_count": len(files),
            "files": files,
            "contract": contract,
            "has_frontend": any(f.startswith("frontend/") for f in files),
            "has_backend": any(f.startswith("backend/") for f in files),
            "has_database": any(f.startswith("database/") for f in files),
            "has_tests": any(f.startswith("tests/") for f in files),
        }

    def prepare(self, spec: dict[str, Any], blueprint_id: str = "") -> dict[str, Any]:
        app_path = self._app_path(spec)
        inspection = self.inspect(app_path)
        contract = inspection.get("contract") or {}
        present = {
            "frontend": inspection["has_frontend"] or spec.get("kind", "web") in {"web", "fullstack", "mobile"},
            "backend": inspection["has_backend"] or spec.get("kind", "web") in {"web", "fullstack", "api", "mobile"},
            "database": inspection["has_database"] or spec.get("database", "none") != "none",
        }
        modules = []
        for key, title, kind in self.MODULES:
            if key == "data" and not present["database"]:
                continue
            if key == "integration" and not (present["frontend"] and present["backend"]):
                continue
            modules.append({
                "id": f"mod_{key}",
                "key": key,
                "title": title,
                "kind": kind,
                "status": "pending",
                "target": str(app_path),
                "files": self._target_files(key, inspection["files"]),
                "contract_items": self._contract_items(key, contract),
            })
        state = {
            "id": hashlib.sha256((str(app_path) + str(time.time())).encode()).hexdigest()[:16],
            "blueprint_id": blueprint_id,
            "app": inspection,
            "modules": modules,
            "status": "ready",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._save(state)
        return {"ok": True, "state": state}

    def _target_files(self, key: str, files: list[str]) -> list[str]:
        if key == "frontend":
            return [f for f in files if f.startswith("frontend/")]
        if key == "backend":
            return [f for f in files if f.startswith("backend/")]
        if key == "data":
            return [f for f in files if f.startswith("database/")]
        if key == "quality":
            return [f for f in files if f.startswith("tests/") or f.startswith("docs/")]
        return [f for f in files if f.startswith(("frontend/", "backend/", "database/"))]

    def _contract_items(self, key: str, contract: dict[str, Any]) -> list[str]:
        if key == "frontend":
            return [str(x.get("name", x)) for x in contract.get("screens", [])]
        if key == "backend":
            return [str(x.get("path", x)) for x in contract.get("endpoints", [])]
        if key == "data":
            return [str(x.get("name", x)) for x in contract.get("entities", [])]
        if key == "integration":
            return [str(x) for x in contract.get("user_flows", [])]
        return [str(x.get("text", x)) for x in contract.get("acceptance_criteria", [])]

    def prompt(self, module_id: str) -> dict[str, Any]:
        state = self._load()
        if not state:
            return {"ok": False, "error": "nenhuma evolução preparada"}
        module = next((m for m in state["modules"] if m["id"] == module_id), None)
        if not module:
            return {"ok": False, "error": "módulo não encontrado"}
        prompt = (
            f"Evoluir o módulo {module['key']} do aplicativo em {module['target']}.\n"
            f"Objetivo: {module['title']}.\n"
            f"Arquivos alvo: {', '.join(module['files']) or 'nenhum arquivo pré-existente; criar quando necessário'}.\n"
            f"Itens do contrato: {', '.join(module['contract_items']) or 'usar o contrato completo'}.\n"
            "Preserve funcionalidades existentes, faça mudanças mínimas e verificáveis, "
            "execute testes relevantes e não altere módulos não relacionados sem necessidade."
        )
        return {"ok": True, "module": module, "prompt": prompt}

    def _module_path(self, module: dict[str, Any]) -> Path:
        return Path(module["target"]).resolve()

    def validate(self, module_id: str) -> dict[str, Any]:
        """Run a focused verification gate for one application module.

        The gate deliberately uses the generated application's own tests for
        integration/quality while keeping frontend/backend/data checks narrow,
        so a failure in one area does not automatically invalidate unrelated
        modules.
        """
        state = self._load()
        if not state:
            return {"ok": False, "error": "nenhuma evolução preparada"}
        module = next((m for m in state["modules"] if m["id"] == module_id), None)
        if not module:
            return {"ok": False, "error": "módulo não encontrado"}
        root = self._module_path(module)
        key = module["key"]
        checks: list[dict[str, Any]] = []

        def check(name: str, command: str, cwd: Path | None = None):
            result = self.agent.terminal.run(command, str(cwd or root))
            result["passed"] = bool(result.get("ok"))
            result["diagnostic"] = diagnose(result)
            checks.append({"name": name, **result})
            return result

        if not root.exists():
            return {"ok": False, "module_id": module_id, "error": "aplicativo não encontrado", "checks": []}

        if key == "frontend":
            check("frontend_presence", "test -f frontend/index.html")
        elif key == "backend":
            check("backend_compile", "python -m py_compile backend/main.py")
        elif key == "data":
            check("database_bootstrap", "python -c \"from backend.main import init_db; init_db(); from pathlib import Path; assert Path('database/app.db').exists()\"")
        elif key in {"integration", "quality"}:
            check("generated_tests", "python -m pytest -q tests")
        else:
            check("module_presence", "test -d .")

        ok = all(c.get("passed") for c in checks)
        return {
            "ok": ok,
            "module_id": module_id,
            "module": module,
            "checks": checks,
            "failed_checks": [c for c in checks if not c.get("passed")],
        }

    def affected_modules(self, comparison: dict[str, Any]) -> dict[str, Any]:
        """Map actual file changes to the smallest set of affected modules."""
        state = self._load()
        if not state:
            return {"ok": False, "error": "nenhuma evolução preparada"}
        changed = set(comparison.get("actual_files", []))
        affected = []
        for module in state.get("modules", []):
            targets = set(module.get("files", []))
            key = module.get("key", "")
            prefix = {
                "frontend": "frontend/", "backend": "backend/",
                "data": "database/", "integration": "", "quality": "tests/",
            }.get(key, "")
            direct = bool(changed & targets)
            related = bool(prefix and any(p.startswith(prefix) for p in changed))
            cross = key == "integration" and bool(changed & {p for m in state.get("modules", []) for p in m.get("files", []) if p.startswith(("frontend/", "backend/", "database/"))})
            if direct or related or cross:
                affected.append({"module_id": module["id"], "key": key, "reason": "direct" if direct else "dependency"})
        return {"ok": True, "changed_files": sorted(changed), "affected_modules": affected, "count": len(affected)}

    def regression_plan(self, comparison: dict[str, Any], limit: int = 50) -> dict[str, Any]:
        """Build a focused regression plan from the modules actually affected."""
        affected = self.affected_modules(comparison)
        if not affected.get("ok"):
            return affected
        tests = []
        for item in affected["affected_modules"]:
            module = next((m for m in (self._load() or {}).get("modules", []) if m["id"] == item["module_id"]), None)
            if not module:
                continue
            tests.extend(module.get("files", []))
            tests.extend(module.get("contract_items", []))
        return {"ok": True, "affected_modules": affected["affected_modules"], "changed_files": affected["changed_files"], "hints": sorted(set(tests))[:max(1, int(limit))]}

    def mark(self, module_id: str, status: str, result: dict[str, Any] | None = None) -> dict[str, Any]:
        state = self._load()
        if not state:
            return {"ok": False, "error": "nenhuma evolução preparada"}
        if status not in {"pending", "running", "done", "failed", "blocked"}:
            return {"ok": False, "error": "status inválido"}
        module = next((m for m in state["modules"] if m["id"] == module_id), None)
        if not module:
            return {"ok": False, "error": "módulo não encontrado"}
        module["status"] = status
        if result is not None:
            module["last_result"] = result
        state["status"] = "completed" if all(m["status"] == "done" for m in state["modules"]) else status
        state["updated_at"] = time.time()
        self._save(state)
        return {"ok": True, "module": module, "status": state["status"]}

    def status(self) -> dict[str, Any]:
        state = self._load()
        return {"ok": True, "state": state, "path": str(self.path)}
