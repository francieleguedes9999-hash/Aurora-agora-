from __future__ import annotations
import ast, hashlib, json, re
from pathlib import Path
from typing import Any

IGNORE_DIRS={'.aurora','.git','__pycache__','.pytest_cache','node_modules','.venv','venv'}
TEXT_EXTS={'.py','.js','.ts','.tsx','.jsx','.json','.md','.txt','.html','.css','.scss','.yaml','.yml','.toml','.sql'}

class KnowledgeGraph:
    """Local, deterministic project graph: files, symbols and lightweight relationships."""
    def __init__(self, root: str|Path):
        self.root=Path(root).resolve()
        self.path=self.root/'.aurora'/'knowledge_graph.json'
        self.path.parent.mkdir(parents=True,exist_ok=True)

    def _files(self):
        for p in self.root.rglob('*'):
            if p.is_file() and p.suffix.lower() in TEXT_EXTS and not any(x in IGNORE_DIRS for x in p.relative_to(self.root).parts):
                yield p

    def _save(self, data):
        tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        tmp.replace(self.path)

    def _load(self):
        try:return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:return {'nodes':[],'edges':[],'fingerprint':None}

    def _py_symbols(self, text):
        out=[]
        try: tree=ast.parse(text)
        except SyntaxError:return out
        for n in ast.walk(tree):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                out.append((n.name, 'class' if isinstance(n,ast.ClassDef) else 'function'))
        return out[:300]

    def build(self, force=False):
        files=list(self._files())
        parts=[]; nodes=[]; edges=[]; module_map={}
        for p in files:
            rel=str(p.relative_to(self.root)); text=p.read_text(encoding='utf-8',errors='ignore')
            digest=hashlib.sha256(text.encode()).hexdigest()
            fid=f'file:{rel}'; nodes.append({'id':fid,'type':'file','path':rel,'hash':digest,'size':len(text)})
            stem=p.stem; module_map[stem]=rel
            for name,kind in self._py_symbols(text):
                sid=f'symbol:{rel}:{name}'; nodes.append({'id':sid,'type':kind,'name':name,'path':rel}); edges.append({'source':fid,'target':sid,'type':'defines'})
            parts.append(rel+'\n'+text[:12000])
        file_paths={str(p.relative_to(self.root)):p for p in files}
        for rel,p in file_paths.items():
            text=p.read_text(encoding='utf-8',errors='ignore'); fid=f'file:{rel}'
            if p.suffix=='.py':
                try:
                    tree=ast.parse(text)
                    for n in ast.walk(tree):
                        if isinstance(n,ast.Import):
                            for a in n.names:
                                target=module_map.get(a.name.split('.')[0])
                                if target: edges.append({'source':fid,'target':f'file:{target}','type':'imports'})
                        elif isinstance(n,ast.ImportFrom) and n.module:
                            target=module_map.get(n.module.split('.')[0])
                            if target: edges.append({'source':fid,'target':f'file:{target}','type':'imports'})
                except SyntaxError: pass
            # lightweight endpoint/component/workflow references
            patterns=[(r'/(?:api/)?[A-Za-z0-9_./:-]+','route'),(r'\b(?:fetch|axios)\s*\(\s*[\'\"]([^\'\"]+)', 'api_call')]
            for pat,etype in patterns:
                for m in re.finditer(pat,text):
                    val=m.group(1) if etype=='api_call' else m.group(0)
                    nid=f'{etype}:{val}'
                    if not any(n['id']==nid for n in nodes): nodes.append({'id':nid,'type':etype,'value':val})
                    edges.append({'source':fid,'target':nid,'type':'references'})
        # de-duplicate edges
        seen=set(); dedup=[]
        for e in edges:
            k=(e['source'],e['target'],e['type'])
            if k not in seen: seen.add(k); dedup.append(e)
        fp=hashlib.sha256('\n'.join(parts).encode()).hexdigest()
        data={'version':1,'fingerprint':fp,'nodes':nodes,'edges':dedup}
        self._save(data)
        return {'ok':True,'fingerprint':fp,'nodes':len(nodes),'edges':len(dedup),'rebuilt':True}

    def graph(self, rebuild=False):
        state=self._load()
        if rebuild or not state.get('nodes'): return self.build(force=rebuild)
        return {'ok':True,'fingerprint':state.get('fingerprint'),'nodes':len(state.get('nodes',[])),'edges':len(state.get('edges',[])),'rebuilt':False}

    def query(self, term, limit=20):
        state=self._load()
        if not state.get('nodes'): self.build(); state=self._load()
        q=(term or '').lower(); nodes=[n for n in state['nodes'] if q in json.dumps(n,ensure_ascii=False).lower()]
        ids={n['id'] for n in nodes}; related=[]
        for e in state['edges']:
            if e['source'] in ids or e['target'] in ids: related.append(e)
        return {'ok':True,'nodes':nodes[:limit],'edges':related[:limit*3]}

    def impact(self, target, depth=2, limit=50):
        state=self._load()
        if not state.get('nodes'): self.build(); state=self._load()
        q=target.lower(); ids={n['id'] for n in state['nodes'] if q in n['id'].lower() or q in str(n.get('path','')).lower() or q in str(n.get('name','')).lower()}
        frontier=set(ids); seen=set(ids); edges=[]
        for _ in range(max(1,min(depth,5))):
            nxt=set()
            for e in state['edges']:
                if e['target'] in frontier:
                    edges.append(e); nxt.add(e['source'])
                elif e['source'] in frontier:
                    edges.append(e); nxt.add(e['target'])
            nxt-=seen; seen|=nxt; frontier=nxt
            if not frontier: break
        nodes=[n for n in state['nodes'] if n['id'] in seen]
        return {'ok':True,'target':target,'nodes':nodes[:limit],'edges':edges[:limit*3],'count':len(nodes)}

    def status(self):
        state=self._load(); return {'ok':True,'exists':bool(state.get('nodes')),'fingerprint':state.get('fingerprint'),'nodes':len(state.get('nodes',[])),'edges':len(state.get('edges',[]))}
