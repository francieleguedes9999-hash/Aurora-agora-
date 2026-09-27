from __future__ import annotations
import base64, json, os, urllib.request, urllib.error
from pathlib import Path
from typing import Any

class HTTPMediaProvider:
    """Configurable HTTP media provider.

    The adapter intentionally does not assume a vendor SDK. It sends a JSON
    request to configured image/audio/video endpoints and accepts either a
    returned URL or base64 payload. API keys are read from an environment
    variable and are never persisted by Aurora.
    """
    def __init__(self, root, name: str, config: dict[str, Any]):
        self.root = Path(root) / '.aurora' / 'media' / name
        self.root.mkdir(parents=True, exist_ok=True)
        self.name = name
        self.config = dict(config)

    def _request(self, kind: str, prompt: str, **kwargs):
        endpoint = self.config.get(f'{kind}_endpoint') or self.config.get('endpoint')
        if not endpoint:
            return {'ok': False, 'kind': kind, 'provider': self.name, 'error': f'{kind}_endpoint_not_configured'}
        env_name = self.config.get('api_key_env')
        key = os.getenv(env_name, '') if env_name else ''
        headers = {'Content-Type': 'application/json', **dict(self.config.get('headers') or {})}
        if key:
            headers.setdefault('Authorization', f'Bearer {key}')
        payload = {'prompt': prompt, **kwargs}
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers=headers, method='POST')
        timeout = float(self.config.get('timeout', 120))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                data = json.loads(raw.decode('utf-8'))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8', errors='replace')[-2000:]
            return {'ok': False, 'kind': kind, 'provider': self.name, 'error': f'http_{exc.code}', 'details': body}
        except Exception as exc:
            return {'ok': False, 'kind': kind, 'provider': self.name, 'error': str(exc)}
        return self._materialize(kind, data)

    def _materialize(self, kind: str, data: Any):
        item = data
        if isinstance(data, dict):
            if isinstance(data.get('data'), list) and data['data']:
                item = data['data'][0]
            elif isinstance(data.get('result'), dict):
                item = data['result']
        if isinstance(item, str):
            item = {'url': item}
        if not isinstance(item, dict):
            return {'ok': False, 'kind': kind, 'provider': self.name, 'error': 'unsupported_provider_response'}
        url = item.get('url') or item.get('output_url')
        encoded = item.get('b64_json') or item.get('base64') or item.get('data_base64')
        if encoded:
            ext = {'image': 'png', 'audio': 'mp3', 'video': 'mp4'}[kind]
            path = self.root / f'generated_{len(list(self.root.iterdir()))+1}.{ext}'
            path.write_bytes(base64.b64decode(encoded))
            return {'ok': True, 'kind': kind, 'provider': self.name, 'path': str(path), 'ai_generated': True, 'response': data}
        if url:
            return {'ok': True, 'kind': kind, 'provider': self.name, 'url': url, 'ai_generated': True, 'response': data}
        return {'ok': False, 'kind': kind, 'provider': self.name, 'error': 'provider_response_has_no_url_or_base64', 'response': data}

    def image(self, prompt, **kwargs): return self._request('image', prompt, **kwargs)
    def audio(self, prompt, **kwargs): return self._request('audio', prompt, **kwargs)
    def video(self, prompt, **kwargs): return self._request('video', prompt, **kwargs)
