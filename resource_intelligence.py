from __future__ import annotations
import json, os, shutil, socket, time
from pathlib import Path
from typing import Any

class ResourceIntelligence:
    """Lightweight local resource inspection and scheduling recommendations."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.path = self.root / '.aurora' / 'resources.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self):
        try: return json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError): return {'checks': []}

    def _save(self):
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding='utf-8')

    def inspect(self, path: str | Path | None = None) -> dict[str, Any]:
        target = Path(path or self.root).resolve()
        usage = shutil.disk_usage(target if target.exists() else self.root)
        cpu = os.cpu_count() or 1
        available_memory = None
        try:
            import resource
            # Linux/macOS resource reports process memory, not total RAM; keep it clearly named.
            available_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        except Exception:
            pass
        result = {'ok': True, 'cpu_count': cpu, 'disk_free_bytes': usage.free,
                  'disk_total_bytes': usage.total, 'process_maxrss': available_memory,
                  'timestamp': time.time()}
        self.state.setdefault('checks', []).append(result)
        self.state['checks'] = self.state['checks'][-50:]
        self._save()
        return result

    def check_port(self, port: int, host: str = '127.0.0.1') -> dict[str, Any]:
        try: port = int(port)
        except (TypeError, ValueError): return {'ok': False, 'error': 'porta inválida'}
        if not 1 <= port <= 65535: return {'ok': False, 'error': 'porta fora do intervalo'}
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.2)
        try:
            busy = s.connect_ex((host, port)) == 0
        finally: s.close()
        return {'ok': True, 'host': host, 'port': port, 'busy': busy, 'available': not busy}

    def recommend_workers(self, requested: int | None = None, tasks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        cpu = os.cpu_count() or 1
        requested_n = max(1, int(requested or cpu))
        task_list = tasks or []
        heavy = sum(1 for t in task_list if str((t.get('payload') or {}).get('resource_class', t.get('resource_class', 'normal'))) in {'heavy','memory'})
        cap = max(1, cpu // 2) if heavy else cpu
        workers = min(requested_n, cap)
        return {'ok': True, 'requested': requested_n, 'recommended': workers, 'cpu_count': cpu,
                'reason': 'tarefas pesadas limitam paralelismo' if heavy else 'limite baseado em CPU'}

    def check(self, requirements: dict[str, Any] | None = None) -> dict[str, Any]:
        req = requirements or {}; info = self.inspect(); problems=[]
        min_free = int(req.get('min_disk_free_bytes', 0) or 0)
        if info['disk_free_bytes'] < min_free: problems.append('disk_free_below_requirement')
        for port in req.get('ports', []) or []:
            p = self.check_port(port)
            if p.get('busy'): problems.append(f'port_busy:{p["port"]}')
        return {'ok': not problems, 'resources': info, 'problems': problems}

    def status(self):
        return {'ok': True, 'last_check': (self.state.get('checks') or [None])[-1], 'checks': len(self.state.get('checks', []))}
