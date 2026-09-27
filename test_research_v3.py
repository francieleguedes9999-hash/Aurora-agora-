import json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from aurora.research import Researcher

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'<html><head><title>Aurora Docs</title></head><body><h1>Pesquisa</h1><p>conteudo importante</p></body></html>'
        self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*a): pass

def test_explicit_url_returns_source():
    server=HTTPServer(('127.0.0.1',0),H); t=threading.Thread(target=server.serve_forever,daemon=True); t.start()
    try:
        out=Researcher(timeout=3).search(f'http://127.0.0.1:{server.server_port}/docs')
        assert out['mode']=='url'; assert out['sources'][0]['title']=='Aurora Docs'; assert 'conteudo importante' in out['sources'][0]['text']
    finally: server.shutdown(); t.join()

def test_unconfigured_query_is_explicit():
    out=Researcher(command=None).search('como criar uma API')
    assert out['available'] is False and out['mode']=='not_configured' and out['sources']==[]
