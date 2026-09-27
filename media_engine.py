from __future__ import annotations
import base64, json, math, shutil, subprocess, wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .media_providers import HTTPMediaProvider

class LocalMediaProvider:
    """Dependency-free local media artifact provider.

    It creates valid deterministic media artifacts (SVG/WAV and, when ffmpeg is
    installed, MP4). It is intentionally not presented as an AI model.
    """
    def __init__(self, root):
        self.root = Path(root) / '.aurora' / 'media'
        self.root.mkdir(parents=True, exist_ok=True)

    def _safe(self, value):
        return ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(value))[:60] or 'media'

    def _base(self, kind, prompt, ext):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        return self.root / f'{stamp}_{self._safe(kind)}_{self._safe(prompt)[:24]}.{ext}'

    def image(self, prompt, **kwargs):
        path = self._base('image', prompt, 'svg')
        title = str(prompt).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="576" viewBox="0 0 1024 576"><rect width="100%" height="100%" fill="#101828"/><text x="512" y="270" text-anchor="middle" fill="white" font-family="sans-serif" font-size="34">Aurora Media</text><text x="512" y="325" text-anchor="middle" fill="#d0d5dd" font-family="sans-serif" font-size="22">{title}</text></svg>'''
        path.write_text(svg, encoding='utf-8')
        return {'ok': True, 'kind': 'image', 'provider': 'local_artifact', 'path': str(path), 'mime_type': 'image/svg+xml', 'ai_generated': False}

    def audio(self, prompt, duration=2.0, sample_rate=16000, **kwargs):
        path = self._base('audio', prompt, 'wav')
        duration = max(0.2, min(float(duration), 30.0))
        freq = 440.0
        frames = int(duration * sample_rate)
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
            for i in range(frames):
                value = int(12000 * math.sin(2 * math.pi * freq * i / sample_rate))
                wf.writeframesraw(value.to_bytes(2, 'little', signed=True))
        return {'ok': True, 'kind': 'audio', 'provider': 'local_artifact', 'path': str(path), 'mime_type': 'audio/wav', 'ai_generated': False}

    def video(self, prompt, duration=3.0, **kwargs):
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            return {'ok': False, 'kind': 'video', 'provider': 'local_artifact', 'error': 'ffmpeg_not_installed', 'ai_generated': False}
        path = self._base('video', prompt, 'mp4')
        duration = max(1.0, min(float(duration), 30.0))
        cmd = [ffmpeg, '-y', '-f', 'lavfi', '-i', 'color=c=0x101828:s=1024x576:r=24', '-t', str(duration), '-pix_fmt', 'yuv420p', str(path)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        if proc.returncode != 0:
            return {'ok': False, 'kind': 'video', 'provider': 'local_artifact', 'error': proc.stderr[-1000:], 'ai_generated': False}
        return {'ok': True, 'kind': 'video', 'provider': 'local_artifact', 'path': str(path), 'mime_type': 'video/mp4', 'ai_generated': False}

class MediaEngine:
    """Provider-agnostic media boundary for image/audio/video generation."""
    def __init__(self, root):
        self.root = Path(root) / '.aurora' / 'media'
        self.root.mkdir(parents=True, exist_ok=True)
        self.local = LocalMediaProvider(root)
        self.providers = {'local_artifact': self.local}
        self.provider_configs = {}

    def register_provider(self, name: str, provider: Any):
        if not name or not hasattr(provider, 'image') or not hasattr(provider, 'audio') or not hasattr(provider, 'video'):
            raise ValueError('provider must implement image, audio and video')
        self.providers[str(name)] = provider
        return {'ok': True, 'provider': str(name)}

    def configure_http_provider(self, name: str, config: dict[str, Any]):
        name = str(name or '').strip()
        if not name or name == 'local_artifact':
            return {'ok': False, 'error': 'invalid_provider_name'}
        if not isinstance(config, dict):
            return {'ok': False, 'error': 'config_must_be_object'}
        provider = HTTPMediaProvider(self.root.parent.parent.parent, name, config)
        self.providers[name] = provider
        self.provider_configs[name] = {k: v for k, v in config.items() if k not in {'api_key', 'token', 'secret'}}
        return {'ok': True, 'provider': name, 'config': self.provider_configs[name]}

    def generate(self, kind: str, prompt: str, provider='local_artifact', **kwargs):
        kind = str(kind or '').lower().strip()
        if kind not in {'image','audio','video'}: return {'ok': False, 'error': 'unsupported_media_kind'}
        if not str(prompt or '').strip(): return {'ok': False, 'error': 'prompt é obrigatório'}
        selected = self.providers.get(provider)
        if selected is None: return {'ok': False, 'error': 'provider_not_configured', 'provider': provider, 'available_providers': list(self.providers)}
        result = getattr(selected, kind)(prompt, **kwargs)
        result.setdefault('provider', provider); result.setdefault('kind', kind)
        return result

    def status(self):
        return {'ok': True, 'providers': list(self.providers), 'configured_http': self.provider_configs, 'local_provider': {'available': True, 'ffmpeg': bool(shutil.which('ffmpeg'))}}
