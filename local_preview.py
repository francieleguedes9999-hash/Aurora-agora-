from __future__ import annotations
import json, socket
from pathlib import Path
from .visual_preview import VisualPreview

class LocalPreview:
    """Build and optionally serve a safe local HTML preview of an Aurora app."""
    def __init__(self, workspace, execution=None):
        self.root = Path(workspace).resolve()
        self.execution = execution
        self.renderer = VisualPreview(self.root)
        self.state_path = self.root / '.aurora' / 'local_preview.json'
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load()

    def _load(self):
        try: return json.loads(self.state_path.read_text(encoding='utf-8'))
        except Exception: return {'previews': {}}
    def _save(self): self.state_path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding='utf-8')
    def _app(self, app_path):
        p=(self.root / app_path if not Path(app_path).is_absolute() else Path(app_path)).resolve()
        if p != self.root and self.root not in p.parents: raise ValueError('app fora do workspace')
        return p
    def build(self, app_path):
        app=self._app(app_path); result=self.renderer.write_preview(app)
        self.state['previews'][str(app)]={'app_path':str(app),'path':result['path'],'bytes':result['bytes']}
        self._save(); return {'ok':True, **result, 'app_path':str(app)}
    def inspect(self, app_path): return self.renderer.inspect(self._app(app_path))
    def _port(self):
        s=socket.socket(); s.bind(('127.0.0.1',0)); p=s.getsockname()[1]; s.close(); return p
    def serve(self, app_path, port=None, name='preview'):
        built=self.build(app_path); p=self._port() if port is None else int(port)
        app=self._app(app_path); directory=str(app/'frontend')
        command=f'python -m http.server {p} --bind 127.0.0.1 --directory {repr(directory)}'
        if self.execution is None: return {'ok':False,'error':'execution runtime indisponível','built':built}
        started=self.execution.start(command, name=name, host='127.0.0.1')
        if not started.get('ok'): return started
        url=f'http://127.0.0.1:{p}/.aurora-preview.html'
        info={'ok':True,'url':url,'host':'127.0.0.1','port':p,'name':name,'pid':started.get('pid'),'preview':built}
        self.state['previews'][str(app)]['server']=info; self._save(); return info
    def stop(self, name='preview'):
        if self.execution is None: return {'ok':False,'error':'execution runtime indisponível'}
        return self.execution.stop(name)
    def status(self): return {'ok':True,'previews':list(self.state.get('previews',{}).values())}
