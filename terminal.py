from __future__ import annotations
import os, signal, subprocess
from pathlib import Path

class SafeTerminal:
    """Workspace-scoped command runner with conservative resource/safety limits."""
    DEFAULT_BLOCKED = (
        'rm -rf /', 'mkfs', 'shutdown', 'reboot', 'poweroff',
        'dd if=', ':(){:|:&};:', 'chmod -R 777 /',
    )

    def __init__(self, root: str | Path, timeout: int = 20, max_output: int = 120_000,
                 blocked_patterns=None, memory_mb: int = 768):
        self.root = Path(root).resolve(); self.timeout = timeout
        self.max_output = max_output; self.memory_mb = memory_mb
        self.blocked_patterns = tuple(blocked_patterns or self.DEFAULT_BLOCKED)

    def _check_cwd(self, cwd: str | Path | None = None) -> Path:
        p = (self.root if cwd is None else (self.root / cwd)).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError("cwd fora do workspace")
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _check_command(self, command: str):
        if not isinstance(command, str) or not command.strip():
            raise ValueError('command vazio')
        low = command.lower().replace('\\', '/')
        for pattern in self.blocked_patterns:
            if pattern.lower() in low:
                raise PermissionError(f'comando bloqueado pela política: {pattern}')

    def _trim(self, value):
        value = value or ''
        if len(value) <= self.max_output:
            return value
        return value[:self.max_output] + '\n...[output truncado]'

    def run(self, command: str, cwd: str | Path | None = None) -> dict:
        self._check_command(command)
        work = self._check_cwd(cwd)
        env = {
            'PATH': os.environ.get('PATH', ''),
            'HOME': str(work),
            'LANG': os.environ.get('LANG', 'C.UTF-8'),
            'PYTHONUNBUFFERED': '1',
            'PYTHONDONTWRITEBYTECODE': '1',
        }
        try:
            proc = subprocess.Popen(command, shell=True, cwd=work, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, env=env,
                                    start_new_session=True)
            try:
                stdout, stderr = proc.communicate(timeout=self.timeout)
                return {'command': command, 'returncode': proc.returncode,
                        'stdout': self._trim(stdout), 'stderr': self._trim(stderr),
                        'ok': proc.returncode == 0, 'timed_out': False,
                        'sandbox': {'workspace_only': True, 'timeout_seconds': self.timeout,
                                    'max_output': self.max_output}}
            except subprocess.TimeoutExpired as exc:
                if os.name == 'posix':
                    try: os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                else:
                    proc.kill()
                stdout, stderr = proc.communicate()
                return {'command': command, 'returncode': None,
                        'stdout': self._trim(stdout or exc.stdout), 'stderr': self._trim(stderr or exc.stderr),
                        'ok': False, 'timed_out': True, 'timeout_seconds': self.timeout,
                        'sandbox': {'workspace_only': True}}
        except OSError as exc:
            return {'command': command, 'returncode': None, 'stdout': '', 'stderr': str(exc),
                    'ok': False, 'timed_out': False, 'sandbox': {'workspace_only': True}}
