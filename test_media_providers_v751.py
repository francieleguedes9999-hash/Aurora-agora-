import base64, json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from aurora.media_engine import MediaEngine

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length','0')) or 0))
        assert body['prompt']
        payload = {'data': [{'b64_json': base64.b64encode(b'AURORA-MEDIA').decode()}]}
        raw = json.dumps(payload).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def log_message(self, *args): pass

def test_http_provider_materializes_base64(tmp_path):
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        m = MediaEngine(tmp_path)
        endpoint = f'http://127.0.0.1:{server.server_address[1]}/generate'
        configured = m.configure_http_provider('test_remote', {'image_endpoint': endpoint})
        assert configured['ok']
        result = m.generate('image', 'aula de história', provider='test_remote')
        assert result['ok'] and result['ai_generated'] is True
        assert Path(result['path']).read_bytes() == b'AURORA-MEDIA'
    finally:
        server.shutdown(); server.server_close()

def test_http_provider_does_not_persist_secret(tmp_path):
    m = MediaEngine(tmp_path)
    result = m.configure_http_provider('remote', {'image_endpoint': 'https://example.invalid', 'api_key_env': 'AURORA_TEST_KEY', 'api_key': 'do-not-store'})
    assert result['ok']
    assert 'do-not-store' not in json.dumps(m.status())
