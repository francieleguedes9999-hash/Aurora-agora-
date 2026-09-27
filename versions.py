from __future__ import annotations
import difflib, hashlib, json, shutil, time, uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

@dataclass
class VersionRecord:
    id: str
    number: int
    label: str
    snapshot: str
    manifest: str
    file_count: int
    created_at: float

class ProjectVersionManager:
    """Persistent project snapshots, comparisons and safe restoration."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.meta = self.root / '.aurora' / 'versions'
        self.snapshots = self.meta / 'snapshots'
        self.meta.mkdir(parents=True, exist_ok=True); self.snapshots.mkdir(parents=True, exist_ok=True)
        self.state_path = self.meta / 'state.json'

    def _load(self):
        try: return json.loads(self.state_path.read_text(encoding='utf-8'))
        except (OSError, ValueError, TypeError, json.JSONDecodeError): return {'current': None, 'history': []}
    def _save(self, data):
        tmp=self.state_path.with_suffix('.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(self.state_path)
    def _files(self):
        for p in sorted(self.root.rglob('*')):
            if not p.is_file(): continue
            rel=p.relative_to(self.root)
            if any(x in {'.aurora','.git','__pycache__','.pytest_cache'} for x in rel.parts): continue
            yield p, rel.as_posix()
    @staticmethod
    def _sha(p):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
        return h.hexdigest()
    def manifest(self):
        return {rel:self._sha(p) for p,rel in self._files()}
    def _record(self, rec):
        state=self._load(); state.setdefault('history',[]).append(asdict(rec)); state['current']=asdict(rec); self._save(state)
    def snapshot(self, label='snapshot'):
        if not self.root.is_dir(): return {'ok':False,'error':'workspace inexistente'}
        state=self._load(); number=len(state.get('history',[]))+1; vid=f'v{number:04d}-{uuid.uuid4().hex[:8]}'
        dest=self.snapshots/vid; dest.mkdir(parents=True)
        manifest={}
        for p,rel in self._files():
            target=dest/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,target); manifest[rel]=self._sha(p)
        mp=dest/'manifest.json'; mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        rec=VersionRecord(vid,number,label,str(dest),str(mp),len(manifest),time.time()); self._record(rec)
        return {'ok':True,'version':asdict(rec),'manifest':manifest}
    def list(self): return {'ok':True,'versions':self._load().get('history',[])}
    def status(self):
        s=self._load(); return {'ok':True,'current':s.get('current'),'count':len(s.get('history',[]))}
    def _get(self, vid): return next((x for x in self._load().get('history',[]) if x['id']==vid),None)
    def diff(self, version_id: str, against: str='current'):
        rec=self._get(version_id)
        if not rec: return {'ok':False,'error':'versão não encontrada'}
        base=json.loads((Path(rec['manifest'])).read_text(encoding='utf-8'))
        other=self.manifest() if against=='current' else json.loads(Path(self._get(against)['manifest']).read_text(encoding='utf-8')) if self._get(against) else None
        if other is None: return {'ok':False,'error':'versão de comparação não encontrada'}
        added=sorted(set(other)-set(base)); removed=sorted(set(base)-set(other)); changed=sorted(k for k in set(base)&set(other) if base[k]!=other[k])
        return {'ok':True,'version_id':version_id,'against':against,'added':added,'removed':removed,'changed':changed,'counts':{'added':len(added),'removed':len(removed),'changed':len(changed)}}
    def restore(self, version_id: str, target: str|Path|None=None, allow_workspace=False):
        rec=self._get(version_id)
        if not rec: return {'ok':False,'error':'versão não encontrada'}
        dest=(Path(target).expanduser().resolve() if target else self.root)
        if dest==self.root and not allow_workspace: return {'ok':False,'error':'restauração sobre workspace exige allow_workspace=True'}
        if dest!=self.root and self.root in dest.parents: return {'ok':False,'error':'destino interno do workspace bloqueado'}
        snap=Path(rec['snapshot']); manifest=json.loads(Path(rec['manifest']).read_text(encoding='utf-8'))
        dest.mkdir(parents=True,exist_ok=True)
        for rel in manifest:
            src=snap/rel; out=dest/rel; out.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,out)
        if dest==self.root:
            current=self.manifest(); stale=set(current)-set(manifest)
            for rel in stale:
                p=self.root/rel
                if p.exists() and p.is_file(): p.unlink()
        return {'ok':True,'version_id':version_id,'destination':str(dest),'file_count':len(manifest)}
    def history(self, limit=20): return {'ok':True,'versions':self._load().get('history',[])[-max(1,limit):]}
