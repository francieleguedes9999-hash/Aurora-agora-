from __future__ import annotations
import json
import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Project:
    id: str
    name: str
    path: str
    description: str = ''
    created_at: str = ''
    updated_at: str = ''
    active: bool = False


class ProjectManager:
    """Persistent local registry for projects managed by an Aurora workspace."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.dir = self.root / '.aurora'
        self.path = self.dir / 'projects.json'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.projects: list[Project] = self._load()

    def _load(self) -> list[Project]:
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return [Project(**item) for item in data.get('projects', [])]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return []

    def _save(self) -> None:
        self.path.write_text(json.dumps({'projects': [asdict(p) for p in self.projects]}, ensure_ascii=False, indent=2), encoding='utf-8')

    @staticmethod
    def _safe_name(name: str) -> str:
        value = re.sub(r'[^A-Za-z0-9._-]+', '-', name.strip()).strip('-')
        if not value:
            raise ValueError('nome de projeto inválido')
        return value

    def register(self, name: str, path: str | Path, description: str = '') -> Project:
        clean = self._safe_name(name)
        target = Path(path).expanduser().resolve()
        existing = next((p for p in self.projects if Path(p.path).resolve() == target), None)
        if existing:
            existing.name = clean
            existing.description = description or existing.description
            existing.updated_at = _now()
            self._save()
            return existing
        now = _now()
        project = Project(uuid.uuid4().hex[:12], clean, str(target), description, now, now, not self.projects)
        self.projects.append(project)
        self._save()
        return project

    def create(self, name: str, description: str = '') -> Project:
        clean = self._safe_name(name)
        target = self.root / 'projects' / clean
        target.mkdir(parents=True, exist_ok=True)
        return self.register(clean, target, description)

    def list(self) -> list[Project]:
        return list(self.projects)

    def get(self, project_id: str) -> Project:
        for p in self.projects:
            if p.id == project_id:
                return p
        raise KeyError(f'projeto não encontrado: {project_id}')

    def active(self) -> Project | None:
        return next((p for p in self.projects if p.active), None)

    def activate(self, project_id: str) -> Project:
        selected = self.get(project_id)
        for p in self.projects:
            p.active = p.id == project_id
            if p.active:
                p.updated_at = _now()
        self._save()
        return selected

    def remove(self, project_id: str, delete_files: bool = False) -> Project:
        project = self.get(project_id)
        self.projects = [p for p in self.projects if p.id != project_id]
        if delete_files:
            target = Path(project.path).resolve()
            # Only allow deletion of projects inside the manager's projects directory.
            allowed = (self.root / 'projects').resolve()
            if allowed not in target.parents:
                raise ValueError('remoção de arquivos fora do diretório de projetos bloqueada')
            import shutil
            if target.exists():
                shutil.rmtree(target)
        if self.projects and not any(p.active for p in self.projects):
            self.projects[0].active = True
        self._save()
        return project

    def summary(self) -> dict[str, Any]:
        active = self.active()
        return {'count': len(self.projects), 'active_id': active.id if active else None, 'projects': [asdict(p) for p in self.projects]}
