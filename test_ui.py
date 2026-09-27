import json, threading, urllib.request
from aurora.agent import Agent
from aurora.ui import AuroraUI

def test_ui_status_and_files(tmp_path):
    agent=Agent(tmp_path)
    server_cls=__import__('http.server', fromlist=['ThreadingHTTPServer']).ThreadingHTTPServer
    server=server_cls(('127.0.0.1',0), AuroraUI(agent).handler())
    t=threading.Thread(target=server.serve_forever, daemon=True); t.start()
    port=server.server_address[1]
    status=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/status'))
    files=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/api/files'))
    assert 'workspace' in status and files['files']==[]
    server.shutdown(); t.join(timeout=2); server.server_close()
