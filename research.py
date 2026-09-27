import json, os, re, subprocess
from html import unescape
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

class Researcher:
    """Pesquisa externa por comando configurado e leitura direta de URLs.

    O comando externo recebe JSON no stdin e pode devolver JSON/texto.
    URLs explícitas podem ser buscadas localmente sem dependência externa.
    """
    def __init__(self, command=None, timeout=30, max_bytes=400_000):
        self.command = command or os.getenv('AURORA_RESEARCH_COMMAND')
        self.timeout = timeout
        self.max_bytes = max_bytes

    def available(self):
        return bool(self.command)

    def _fetch_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise ValueError('apenas URLs http/https são permitidas')
        req = Request(url, headers={'User-Agent': 'Aurora/3.0 research agent'})
        with urlopen(req, timeout=self.timeout) as response:
            data = response.read(self.max_bytes + 1)
            truncated = len(data) > self.max_bytes
            data = data[:self.max_bytes]
            content_type = response.headers.get('Content-Type', '')
            final_url = response.geturl()
        text = data.decode('utf-8', errors='replace')
        if 'html' in content_type or '<html' in text.lower():
            title = re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S)
            text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.I | re.S)
            text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.I | re.S)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = unescape(re.sub(r'\s+', ' ', text)).strip()
        else:
            title = None
            text = text.strip()
        return {
            'url': final_url,
            'title': unescape(title.group(1)).strip() if title else final_url,
            'text': text,
            'truncated': truncated,
            'content_type': content_type,
        }

    def search(self, query, context=None):
        # URL explícita: coleta fonte verificável diretamente.
        if re.match(r'^https?://', query.strip(), re.I):
            try:
                source = self._fetch_url(query.strip())
                return {'available': True, 'query': query, 'mode': 'url', 'sources': [source]}
            except (URLError, HTTPError, TimeoutError, ValueError, OSError) as e:
                return {'available': True, 'query': query, 'mode': 'url', 'sources': [], 'error': str(e)}

        if not self.command:
            return {
                'available': False,
                'query': query,
                'mode': 'not_configured',
                'sources': [],
                'message': 'Pesquisa por consulta exige AURORA_RESEARCH_COMMAND. Para uma fonte específica, forneça uma URL http/https.'
            }
        payload = json.dumps({'query': query, 'context': context or {}}, ensure_ascii=False)
        p = subprocess.run(self.command, input=payload, text=True, shell=True,
                           capture_output=True, timeout=self.timeout)
        if p.returncode:
            raise RuntimeError(p.stderr.strip() or 'pesquisador retornou erro')
        raw = p.stdout.strip()
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {'text': raw}
        sources = result.get('sources', []) if isinstance(result, dict) else []
        return {'available': True, 'query': query, 'mode': 'external_command', 'result': result, 'sources': sources}
