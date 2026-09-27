from pathlib import Path

class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.root.mkdir(parents=True, exist_ok=True)
    def path(self, rel):
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents: raise ValueError('caminho fora do workspace')
        return p
    def list_files(self): return [str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()]
    def read_file(self, path): return self.path(path).read_text(encoding='utf-8')
    def write_file(self, path, content):
        p=self.path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content, encoding='utf-8'); return str(p.relative_to(self.root))

class FileTools:
    def __init__(self, workspace, researcher=None):
        self.ws=workspace
        self.researcher=researcher
    def call(self, name, args):
        if name=='list_files': return {'files': self.ws.list_files()}
        if name=='read_file': return {'path':args['path'], 'content':self.ws.read_file(args['path'])}
        if name=='write_file': return {'path':self.ws.write_file(args['path'], args.get('content','')), 'written':True}
        if name=='research':
            if self.researcher is None: raise ValueError('pesquisa indisponível')
            return self.researcher.search(args['query'], args.get('context'))
        raise ValueError(f'ferramenta desconhecida: {name}')
