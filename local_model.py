from __future__ import annotations
import json, os, shutil, subprocess, urllib.request, urllib.error
from typing import Any

class LocalModelManager:
    """Safe management boundary for a local Ollama runtime.

    It never downloads a model unless pull() is explicitly requested.
    """
    def __init__(self, base_url: str | None = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv('AURORA_LOCAL_BASE_URL') or 'http://127.0.0.1:11434').rstrip('/')
        self.timeout = timeout

    def runtime(self) -> dict[str, Any]:
        cli = shutil.which('ollama')
        reachable = False
        error = None
        try:
            with urllib.request.urlopen(self.base_url + '/api/tags', timeout=1.5) as r:
                reachable = r.status == 200
        except Exception as exc:
            error = str(exc)
        return {'runtime': 'ollama', 'base_url': self.base_url, 'cli': cli or None,
                'reachable': reachable, 'error': error}

    def list_models(self) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(self.base_url + '/api/tags', timeout=self.timeout) as r:
                body = json.loads(r.read().decode('utf-8'))
            return {'ok': True, 'models': body.get('models', [])}
        except Exception as exc:
            return {'ok': False, 'models': [], 'error': str(exc)}

    def pull(self, model: str) -> dict[str, Any]:
        model = (model or '').strip()
        if not model:
            return {'ok': False, 'error': 'model obrigatório'}
        cli = shutil.which('ollama')
        if not cli:
            return {'ok': False, 'error': 'Ollama CLI não encontrado; instale o Ollama para fazer pull de modelos.'}
        try:
            p = subprocess.run([cli, 'pull', model], text=True, capture_output=True,
                               timeout=max(self.timeout, 300))
            return {'ok': p.returncode == 0, 'model': model,
                    'stdout': p.stdout[-4000:], 'stderr': p.stderr[-4000:],
                    'returncode': p.returncode}
        except subprocess.TimeoutExpired:
            return {'ok': False, 'model': model, 'error': 'download excedeu o tempo limite'}
        except Exception as exc:
            return {'ok': False, 'model': model, 'error': str(exc)}

    def select_for_task(self, task: str, models: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Select an already-installed local model using deterministic task hints.

        Selection never downloads a model. It only returns the chosen installed model.
        """
        task = (task or '').lower()
        items = models if models is not None else self.list_models().get('models', [])
        names = [str(item.get('name') or item.get('model') or '').strip() for item in items]
        names = [name for name in names if name]
        if not names:
            return {'ok': False, 'selected': None, 'reason': 'nenhum modelo local instalado'}
        groups = [
            (('imagem', 'visão', 'vision', 'foto', 'vídeo', 'video'), ('llava', 'vision', 'qwen2-vl', 'minicpm-v')),
            (('código', 'codigo', 'programação', 'programacao', 'programar', 'app', 'software', 'python', 'javascript'), ('coder', 'code', 'qwen2.5-coder', 'qwen3-coder', 'deepseek-coder', 'starcoder')),
        ]
        selected = None
        for keywords, hints in groups:
            if any(word in task for word in keywords):
                selected = next((name for name in names if any(hint in name.lower() for hint in hints)), None)
                if selected:
                    break
        if not selected:
            selected = names[0]
        return {'ok': True, 'selected': selected, 'available': names, 'reason': 'task_match' if selected != names[0] else 'default'}

    def status(self) -> dict[str, Any]:
        runtime = self.runtime()
        models = self.list_models() if runtime['reachable'] else {'ok': False, 'models': []}
        configured = os.getenv('AURORA_LOCAL_MODEL') or os.getenv('AURORA_MODEL')
        return {'ok': runtime['reachable'], 'runtime': runtime, 'configured_model': configured,
                'models': models.get('models', []), 'model_count': len(models.get('models', []))}
