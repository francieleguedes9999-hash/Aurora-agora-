from __future__ import annotations
import hashlib, json, secrets, threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class AuroraAPI:
    """Local-first HTTP API with hashed persistent bearer keys."""
    def __init__(self, agent, root):
        self.agent = agent; self.root = Path(root) / '.aurora'; self.root.mkdir(parents=True, exist_ok=True)
        self.keys_file = self.root / 'api_keys.json'; self._lock = threading.Lock(); self._server = None
    def _load(self):
        if not self.keys_file.exists(): return []
        try: return json.loads(self.keys_file.read_text(encoding='utf-8'))
        except Exception: return []
    def _save(self, items): self.keys_file.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding='utf-8')
    def create_key(self, name='app'):
        raw = 'aurora_sk_' + secrets.token_urlsafe(32); digest = hashlib.sha256(raw.encode()).hexdigest()
        with self._lock:
            items = self._load(); items.append({'name': name, 'sha256': digest, 'created_at': datetime.now(timezone.utc).isoformat(), 'active': True}); self._save(items)
        return {'ok': True, 'name': name, 'key': raw, 'warning': 'Guarde esta chave; ela não é recuperada em texto puro.'}
    def revoke_key(self, key):
        digest = hashlib.sha256(str(key).encode()).hexdigest()
        with self._lock:
            items = self._load(); changed = False
            for item in items:
                if item.get('sha256') == digest: item['active'] = False; changed = True
            self._save(items)
        return {'ok': changed}
    def valid(self, key):
        if not key: return False
        digest = hashlib.sha256(str(key).encode()).hexdigest()
        return any(x.get('sha256') == digest and x.get('active', False) for x in self._load())
    def status(self):
        return {'ok': True, 'keys': [{'name':x.get('name'),'created_at':x.get('created_at'),'active':x.get('active',False)} for x in self._load()]}
    def handle(self, method, path, body, auth):
        if path == '/v1/status' and method == 'GET': return 200, self.status()
        if not self.valid(auth): return 401, {'ok': False, 'error': 'invalid_api_key'}
        if path == '/v1/questions' and method == 'POST':
            return 200, self.agent.question_generator.generate(body.get('topic',''), body.get('count',5), body.get('difficulty','medium'), body.get('type','multiple_choice'), body.get('context',''))
        if path == '/v1/chat' and method == 'POST':
            msg = str(body.get('message',''))
            if not msg: return 400, {'ok': False, 'error': 'message é obrigatório'}
            return 200, {'ok': True, 'response': self.agent.model.ask(msg, inputs=body.get('inputs'))}
        if path == '/v1/media' and method == 'POST':
            return 200, self.agent.media.generate(body.get('kind','image'), body.get('prompt',''), body.get('provider','local_artifact'), **body.get('options', {}))
        return 404, {'ok': False, 'error': 'not_found'}
    def serve(self, host='127.0.0.1', port=8787):
        gateway = self
        class Handler(BaseHTTPRequestHandler):
            def _send(self, code, payload):
                raw=json.dumps(payload,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
            def do_GET(self):
                auth=self.headers.get('Authorization','').removeprefix('Bearer ').strip(); code,payload=gateway.handle('GET',self.path,{},auth); self._send(code,payload)
            def do_POST(self):
                try: body=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0')) or 0) or b'{}')
                except Exception: self._send(400,{'ok':False,'error':'invalid_json'}); return
                auth=self.headers.get('Authorization','').removeprefix('Bearer ').strip(); code,payload=gateway.handle('POST',self.path,body,auth); self._send(code,payload)
            def log_message(self,*args): pass
        self._server=ThreadingHTTPServer((host,int(port)),Handler); return self._server
