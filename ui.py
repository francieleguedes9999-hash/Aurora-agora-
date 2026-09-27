import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path
from .local_runtime import LocalRuntimePolicy

HTML = '''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Aurora</title><style>body{font-family:system-ui;margin:0;background:#10131a;color:#eee}header{padding:18px 22px;border-bottom:1px solid #2a3040}main{max-width:1000px;margin:auto;padding:22px}.grid{display:grid;grid-template-columns:2fr 1fr;gap:18px}.card{background:#171c25;border:1px solid #2a3040;border-radius:14px;padding:16px}textarea{width:100%;box-sizing:border-box;background:#0d1117;color:#eee;border:1px solid #394254;border-radius:10px;padding:12px;min-height:110px}button{margin-top:10px;padding:10px 16px;border:0;border-radius:9px;cursor:pointer}pre{white-space:pre-wrap;word-break:break-word;max-height:420px;overflow:auto}.muted{color:#9ba5b5}@media(max-width:700px){.grid{grid-template-columns:1fr}}</style></head><body><header><strong>✦ Aurora</strong><span class="muted"> — assistente pessoal de desenvolvimento · acesso local, sem login</span></header><main><div class="grid"><section class="card"><h2>Nova tarefa</h2><textarea id="req" placeholder="Descreva o aplicativo ou tarefa..."></textarea><button onclick="run()">Executar Aurora</button><h3>Resultado</h3><pre id="out">Pronta.</pre></section><aside class="card"><h2>Workspace</h2><div id="status">Carregando…</div><h3>Projetos</h3><div id="projects"></div><input id="pname" placeholder="Nome do projeto"><button onclick="createProject()">Criar projeto</button><h3>Sessões</h3><pre id="sessions"></pre><h3>Arquivos</h3><pre id="files"></pre></aside></div></main><script>async function get(u){let r=await fetch(u);return r.json()} async function load(){let s=await get('/api/status');document.getElementById('status').textContent=JSON.stringify(s,null,2);let f=await get('/api/files');document.getElementById('files').textContent=f.files.join('\\n')} async function createProject(){let name=document.getElementById('pname').value.trim();if(!name)return;await fetch('/api/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action:'create',name})});document.getElementById('pname').value='';load()} async function activateProject(id){await fetch('/api/projects',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({action:'activate',project_id:id})});load()} async function run(){let q=document.getElementById('req').value.trim();if(!q)return;document.getElementById('out').textContent='Executando…';let r=await fetch('/api/run',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({request:q})});document.getElementById('out').textContent=JSON.stringify(await r.json(),null,2);load()}load()</script></body></html>'''

class AuroraUI:
    def __init__(self, agent):
        self.agent = agent
        self.runtime_policy = LocalRuntimePolicy(agent.local_access)
    def handler(self):
        agent=self.agent
        class Handler(BaseHTTPRequestHandler):
            def _json(self, obj, status=200):
                data=json.dumps(obj, ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
            def do_GET(self):
                path=urlparse(self.path).path
                if path=='/':
                    data=HTML.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data); return
                if path=='/api/status': self._json({'workspace':str(agent.workspace.root),'sessions':len(agent.sessions.list()),'cycle':agent.cycle.status(),'access':agent.local_access.status()}); return
                if path=='/api/projects': self._json(agent.projects.summary()); return
                if path=='/api/sessions': self._json({'sessions': agent.sessions.list()}); return
                if path=='/api/plan': self._json(agent.planner.context()); return
                if path=='/api/files':
                    files=[]
                    for p in agent.workspace.root.rglob('*'):
                        if p.is_file() and '.aurora' not in p.parts: files.append(str(p.relative_to(agent.workspace.root)))
                    self._json({'files':sorted(files)[:500]}); return
                self._json({'error':'not found'},404)
            def do_POST(self):
                path=urlparse(self.path).path
                if path=='/api/projects':
                    try:
                        n=int(self.headers.get('Content-Length','0')); body=json.loads(self.rfile.read(n) or b'{}')
                        action=body.get('action','list'); result=agent._call('projects', body)
                        self._json(result); return
                    except Exception as e: self._json({'error':str(e)},400); return
                if path!='/api/run': self._json({'error':'not found'},404); return
                try:
                    n=int(self.headers.get('Content-Length','0')); body=json.loads(self.rfile.read(n) or b'{}'); req=str(body.get('request','')).strip()
                    if not req: self._json({'error':'request ausente'},400); return
                    self._json(agent.run_cycle(req))
                except Exception as e: self._json({'error':str(e)},500)
            def log_message(self,*args): pass
        return Handler
    def serve(self, host='127.0.0.1', port=8787, allow_remote=False):
        self.runtime_policy.validate_bind(host, allow_remote=allow_remote)
        server=ThreadingHTTPServer((host,port),self.handler()); server.serve_forever()
