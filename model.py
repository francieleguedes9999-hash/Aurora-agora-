import json, os, subprocess, urllib.request, urllib.error

class Model:
    """Provider boundary for Aurora's cognitive brain.

    Modes:
      - command: AURORA_MODEL_COMMAND
      - openai-compatible HTTP: AURORA_API_KEY + AURORA_MODEL
      - ollama: local Ollama HTTP runtime (no API key)
      - local: local runtime, preferring Ollama then local command
      - auto: local command first, then local Ollama, then OpenAI-compatible HTTP
    """
    def __init__(self, command=None, provider=None, api_key=None, model=None, base_url=None, timeout=120):
        self.command = command or os.getenv('AURORA_MODEL_COMMAND')
        self.provider = (provider or os.getenv('AURORA_MODEL_PROVIDER') or 'auto').lower()
        self.api_key = api_key or os.getenv('AURORA_API_KEY')
        self.model = model or os.getenv('AURORA_MODEL')
        self.base_url = (base_url or os.getenv('AURORA_API_BASE') or 'https://api.openai.com/v1').rstrip('/')
        self.local_base_url = (os.getenv('AURORA_LOCAL_BASE_URL') or 'http://127.0.0.1:11434').rstrip('/')
        self.local_model = model or os.getenv('AURORA_LOCAL_MODEL') or self.model
        self.timeout = int(timeout or os.getenv('AURORA_MODEL_TIMEOUT', '120'))

    def _ollama_available(self):
        try:
            with urllib.request.urlopen(self.local_base_url + '/api/tags', timeout=1.5) as response:
                return response.status == 200
        except Exception:
            return False

    def available(self):
        if self.provider in {'command', 'auto', 'local'} and self.command:
            return True
        if self.provider in {'ollama', 'local', 'auto'} and self.local_model and self._ollama_available():
            return True
        return bool(self.api_key and self.model and self.provider in {'auto', 'openai', 'openai-compatible'})

    def status(self):
        return {
            'provider': self.provider,
            'available': self.available(),
            'local': {
                'runtime': 'ollama',
                'base_url': self.local_base_url,
                'model': self.local_model,
                'configured': bool(self.local_model),
                'reachable': self._ollama_available(),
            },
            'external': {'configured': bool(self.api_key and self.model)},
        }

    def _command(self, prompt):
        p = subprocess.run(self.command, input=prompt, text=True, shell=True, capture_output=True, timeout=self.timeout)
        if p.returncode:
            raise RuntimeError(p.stderr.strip() or 'modelo retornou erro')
        return p.stdout.strip()

    def _ollama(self, prompt, inputs=None):
        if not self.local_model:
            raise RuntimeError('configure AURORA_LOCAL_MODEL para usar o modelo local')
        if inputs:
            # Ollama text runtime receives a textual placeholder; multimodal adapters remain separate.
            prompt = prompt + "\n[entradas multimodais anexadas: " + str(len(inputs)) + "]"
        payload = {'model': self.local_model, 'prompt': prompt, 'stream': False, 'options': {'temperature': 0.1}}
        req = urllib.request.Request(
            self.local_base_url + '/api/generate', data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'Ollama retornou {exc.code}: {detail[:500]}') from exc
        text = body.get('response')
        if not text:
            raise RuntimeError('Ollama não retornou conteúdo')
        return str(text).strip()

    def _http(self, prompt, inputs=None):
        if not self.api_key or not self.model:
            raise RuntimeError('configure AURORA_API_KEY e AURORA_MODEL para o provedor HTTP')
        user_content = prompt
        if inputs:
            parts = [{'type': 'text', 'text': prompt}]
            for item in inputs:
                if isinstance(item, dict) and item.get('type') == 'image' and item.get('data'):
                    parts.append({'type': 'image_url', 'image_url': {'url': str(item['data'])}})
            user_content = parts
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': 'Você é o cérebro cognitivo da Aurora. Responda somente JSON de ação: {"tool":"...","args":{...}} ou {"final":"..."}.'},
                {'role': 'user', 'content': user_content},
            ],
            'temperature': 0.1,
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.base_url + '/chat/completions', data=data,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.api_key},
            method='POST')
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')
            raise RuntimeError(f'provedor HTTP retornou {exc.code}: {detail[:500]}') from exc
        choices = body.get('choices') or []
        if not choices:
            raise RuntimeError('resposta HTTP não contém choices')
        content = choices[0].get('message', {}).get('content')
        if isinstance(content, list):
            content = ''.join(x.get('text', '') for x in content if isinstance(x, dict))
        if not content:
            raise RuntimeError('resposta HTTP não contém conteúdo')
        return content.strip()

    def ask(self, prompt, inputs=None):
        if self.provider == 'command' or (self.provider in {'auto', 'local'} and self.command):
            return self._command(prompt)
        if self.provider in {'ollama', 'local', 'auto'} and self.local_model:
            try:
                return self._ollama(prompt, inputs=inputs)
            except Exception:
                if self.provider in {'ollama', 'local'}:
                    raise
        if self.provider in {'openai', 'openai-compatible', 'auto'}:
            return self._http(prompt, inputs=inputs)
        raise RuntimeError(f'provedor não suportado: {self.provider}')
