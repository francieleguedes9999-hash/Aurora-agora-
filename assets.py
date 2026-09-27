import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from html import escape

@dataclass
class Asset:
    name: str
    kind: str
    path: str
    mime: str
    metadata: dict

class AssetManager:
    """Local-first asset pipeline: deterministic SVG assets and video storyboards."""
    def __init__(self, workspace):
        self.root = Path(workspace).resolve()
        self.asset_root = self.root / 'assets'
        self.asset_root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.asset_root / 'manifest.json'

    def _safe(self, name):
        value = re.sub(r'[^a-zA-Z0-9_-]+', '-', name).strip('-_').lower()
        if not value:
            raise ValueError('nome do asset inválido')
        return value

    def _save(self, asset):
        data = []
        if self.manifest_path.exists():
            try: data = json.loads(self.manifest_path.read_text(encoding='utf-8'))
            except Exception: data = []
        data = [x for x in data if x.get('path') != asset.path]
        data.append(asdict(asset))
        self.manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def icon(self, name, label=None, size=128):
        slug = self._safe(name)
        if not 16 <= int(size) <= 2048: raise ValueError('tamanho inválido')
        label = label or name
        path = self.asset_root / f'{slug}.svg'
        text = escape(label[:24])
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" role="img" aria-label="{text}"><rect width="100%" height="100%" rx="24" fill="currentColor"/><text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" font-family="system-ui,sans-serif" font-size="{max(12, size//5)}" fill="white">{escape(label[:4].upper())}</text></svg>\n'''
        path.write_text(svg, encoding='utf-8')
        asset = Asset(name=label, kind='icon', path=str(path.relative_to(self.root)), mime='image/svg+xml', metadata={'size': int(size)})
        self._save(asset)
        return {'ok': True, 'asset': asdict(asset)}

    def storyboard(self, name, scenes):
        slug = self._safe(name)
        if not scenes or not isinstance(scenes, list): raise ValueError('cenas devem ser uma lista não vazia')
        normalized=[]
        for i, scene in enumerate(scenes, 1):
            if isinstance(scene, str): scene={'description': scene}
            normalized.append({'id': i, 'duration': float(scene.get('duration', 3)), 'description': str(scene.get('description','')), 'assets': list(scene.get('assets', []))})
        path = self.asset_root / f'{slug}.storyboard.json'
        path.write_text(json.dumps({'name': name, 'scenes': normalized}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        asset = Asset(name=name, kind='storyboard', path=str(path.relative_to(self.root)), mime='application/json', metadata={'scenes': len(normalized)})
        self._save(asset)
        return {'ok': True, 'asset': asdict(asset), 'scenes': normalized}

    def list(self):
        if not self.manifest_path.exists(): return []
        try: return json.loads(self.manifest_path.read_text(encoding='utf-8'))
        except Exception: return []
