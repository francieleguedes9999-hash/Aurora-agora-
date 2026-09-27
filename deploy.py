from __future__ import annotations
import json, os, re, shlex, time
from dataclasses import dataclass, asdict
from pathlib import Path
from .tools.terminal import SafeTerminal

@dataclass
class DeployConfig:
    provider: str = "local"
    environment: str = "development"
    command: str = ""
    verify_command: str = ""
    rollback_command: str = ""
    timeout: int = 60
    dry_run: bool = False

class DeployManager:
    """Provider-independent deployment orchestration.

    Deployment commands execute inside the Aurora workspace. Secrets are read from
    the process environment and are never written to deploy state.
    """
    PROVIDERS = {"local", "docker", "generic"}

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.state_dir = self.root / ".aurora"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / "deploy.json"
        self.history_path = self.state_dir / "deploy-history.jsonl"

    def _load(self):
        if not self.state_path.exists():
            return {"current": None, "previous": None, "history": []}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return {"current": None, "previous": None, "history": []}

    def _save(self, state):
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.state_path)

    def _redact(self, value):
        if not isinstance(value, str):
            return value
        # Redact common inline secret assignments before persistence.
        value = re.sub(r"(?i)(token|secret|password|api[_-]?key|authorization)\s*=\s*([^\s;\"']+)", r"\1=<REDACTED>", value)
        return value

    def _record(self, event):
        safe = {k: self._redact(v) for k, v in dict(event).items()}
        safe.pop("env", None)
        with self.history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe, ensure_ascii=False) + "\n")

    def validate(self, config: dict | DeployConfig):
        cfg = config if isinstance(config, DeployConfig) else DeployConfig(**{k:v for k,v in config.items() if k in DeployConfig.__dataclass_fields__})
        errors = []
        if cfg.provider not in self.PROVIDERS:
            errors.append(f"provider inválido: {cfg.provider}")
        if not cfg.environment.strip():
            errors.append("environment vazio")
        if cfg.provider == "docker" and not (self.root / "Dockerfile").exists() and not (self.root / "docker-compose.yml").exists() and not (self.root / "compose.yml").exists():
            errors.append("provider docker requer Dockerfile ou compose.yml/docker-compose.yml")
        if cfg.provider in {"local", "generic"} and not cfg.command.strip():
            errors.append("command obrigatório para este provider")
        return {"ok": not errors, "errors": errors, "provider": cfg.provider, "environment": cfg.environment}

    def _config(self, config):
        if isinstance(config, DeployConfig): return config
        return DeployConfig(**{k:v for k,v in config.items() if k in DeployConfig.__dataclass_fields__})

    def plan(self, config):
        cfg = self._config(config)
        validation = self.validate(cfg)
        return {"ok": validation["ok"], "validation": validation, "steps": ["validate", "build/package", "deploy", "verify"], "provider": cfg.provider, "environment": cfg.environment}

    def _run(self, command, timeout):
        return SafeTerminal(self.root, timeout=timeout).run(command)

    def deploy(self, config, package_path: str | None = None, dry_run: bool | None = None):
        cfg = self._config(config)
        validation = self.validate(cfg)
        if not validation["ok"]:
            return {"ok": False, "stage": "validate", "validation": validation}
        is_dry = cfg.dry_run if dry_run is None else dry_run
        state = self._load()
        deployment_id = f"dep-{int(time.time()*1000)}"
        command = cfg.command
        if cfg.provider == "docker" and not command:
            command = "docker compose up -d --build"
        if package_path:
            command = command.replace("{package}", shlex.quote(str(Path(package_path).resolve())))
        result = {"ok": True, "deployment_id": deployment_id, "provider": cfg.provider,
                  "environment": cfg.environment, "dry_run": is_dry, "command": command}
        if not is_dry:
            run = self._run(command, cfg.timeout)
            result["execution"] = run
            if not run.get("ok"):
                result["ok"] = False; result["stage"] = "deploy"
                self._record({"event":"deploy_failed", "deployment_id":deployment_id, "provider":cfg.provider, "environment":cfg.environment, "ts":time.time()})
                return result
            state["previous"] = state.get("current")
            state["current"] = {"deployment_id":deployment_id, "provider":cfg.provider, "environment":cfg.environment,
                                 "command":command, "package_path":str(package_path) if package_path else None,
                                 "created_at":time.time()}
            self._save(state)
            self._record({"event":"deployed", **state["current"]})
        return result

    def verify(self, config):
        cfg = self._config(config)
        if not cfg.verify_command:
            return {"ok": True, "verified": False, "reason": "verify_command não configurado"}
        run = self._run(cfg.verify_command, cfg.timeout)
        self._record({"event":"verify", "ok":run.get("ok"), "ts":time.time()})
        return {"ok": bool(run.get("ok")), "verified": True, "execution": run}

    def rollback(self, config):
        cfg = self._config(config)
        state = self._load()
        previous = state.get("previous")
        if not previous:
            return {"ok": False, "error": "nenhuma implantação anterior disponível"}
        command = cfg.rollback_command
        if not command:
            command = cfg.command
        if not command:
            return {"ok": False, "error": "rollback_command ou command é obrigatório"}
        if cfg.provider == "docker" and not cfg.rollback_command:
            command = "docker compose up -d --build"
        run = self._run(command, cfg.timeout)
        if run.get("ok"):
            state["current"], state["previous"] = previous, state.get("current")
            self._save(state)
        self._record({"event":"rollback", "ok":run.get("ok"), "target":previous.get("deployment_id"), "ts":time.time()})
        return {"ok": bool(run.get("ok")), "target": previous, "execution": run}

    def status(self):
        state = self._load()
        return {"ok": True, **state}
