from __future__ import annotations
import json, os, subprocess, signal
from pathlib import Path
from datetime import datetime, timezone
from .local_runtime import LocalRuntimePolicy

class LocalExecutionRuntime:
    """Local project execution layer. Keeps execution inside the Aurora workspace."""
    def __init__(self, root, terminal=None):
        self.root = Path(root).resolve()
        self.terminal = terminal
        self.policy = LocalRuntimePolicy(None)
        self.state_path = self.root / '.aurora' / 'local_execution.json'
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()

    def _load(self):
        if self.state_path.exists():
            try: return json.loads(self.state_path.read_text(encoding='utf-8'))
            except Exception: pass
        state={'mode':'local','processes':{},'updated_at':self._now()}
        self._save(state); return state

    def _now(self): return datetime.now(timezone.utc).isoformat()
    def _save(self, state=None):
        if state is not None: self._state=state
        self._state['updated_at']=self._now()
        self.state_path.write_text(json.dumps(self._state,ensure_ascii=False,indent=2),encoding='utf-8')

    def _cwd(self, cwd=None):
        p=(self.root / cwd if cwd else self.root).resolve()
        if p != self.root and self.root not in p.parents: raise ValueError('cwd fora do workspace')
        return p

    def inspect(self):
        active=[]
        for name, info in list(self._state.get('processes',{}).items()):
            pid=info.get('pid'); alive=False
            if pid:
                try: os.kill(int(pid),0); alive=True
                except OSError: alive=False
            info['alive']=alive
            if alive: active.append(info)
        self._save(); return {'ok':True,'mode':'local','workspace':str(self.root),'processes':active}

    def run(self, command, cwd=None, timeout=None):
        if self.terminal is not None:
            return self.terminal.run(command, cwd)
        p=self._cwd(cwd)
        return subprocess.run(command,shell=True,cwd=p,capture_output=True,text=True,timeout=timeout or 20).__dict__

    def start(self, command, cwd=None, name='app', host='127.0.0.1'):
        self.policy.validate_bind(host, allow_remote=False)
        work=self._cwd(cwd)
        env=os.environ.copy(); env['HOME']=str(work); env['PYTHONUNBUFFERED']='1'
        proc=subprocess.Popen(command,shell=True,cwd=work,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                              env=env,start_new_session=True)
        self._state.setdefault('processes',{})[name]={'name':name,'pid':proc.pid,'command':command,'cwd':str(work),'host':host,'started_at':self._now()}
        self._save()
        return {'ok':True,'name':name,'pid':proc.pid,'host':host,'command':command}

    def stop(self,name):
        info=self._state.get('processes',{}).get(name)
        if not info: return {'ok':False,'error':'processo não encontrado','name':name}
        pid=info.get('pid')
        try:
            os.killpg(int(pid),signal.SIGTERM) if os.name=='posix' else os.kill(int(pid),signal.SIGTERM)
        except OSError: pass
        info['stopped_at']=self._now(); info['alive']=False
        self._save(); return {'ok':True,'name':name,'pid':pid}

    def status(self): return self.inspect()
