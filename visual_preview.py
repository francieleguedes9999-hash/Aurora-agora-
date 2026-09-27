from __future__ import annotations
import html, json
from pathlib import Path

class VisualPreview:
    """Generate a deterministic local HTML preview and component inspection data."""
    def __init__(self, workspace): self.root = Path(workspace).resolve()
    def _app(self, app_path):
        p=Path(app_path)
        if not p.is_absolute(): p=self.root/p
        p=p.resolve()
        if not (p==self.root or self.root in p.parents): raise ValueError('app fora do workspace')
        return p
    def inspect(self, app_path):
        app=self._app(app_path); data=json.loads((app/'frontend/ui.json').read_text(encoding='utf-8'))
        out=[]
        for i,c in enumerate(data.get('components',[])):
            out.append({'id':c.get('id',f'component-{i}'),'type':c.get('type','unknown'),'label':c.get('label'), 'props':c.get('props',{}), 'index':i})
        return {'theme':data.get('theme',{}),'components':out,'count':len(out)}
    def render(self, app_path):
        app=self._app(app_path); data=json.loads((app/'frontend/ui.json').read_text(encoding='utf-8'))
        theme=data.get('theme',{}); comps=data.get('components',[])
        parts=[]
        for c in comps:
            if c.get('props',{}).get('hidden'): continue
            cid=html.escape(str(c.get('id','component'))); typ=html.escape(str(c.get('type','div'))); label=html.escape(str(c.get('label') or typ.title()))
            cls='app-sidebar' if typ=='sidebar' else 'preview-component'
            if typ=='button': body=f'<button id="{cid}">{label}</button>'
            elif typ in ('form','input'): body=f'<label>{label}<input name="{cid}" /></label>'
            elif typ in ('list','table'): body=f'<section><h3>{label}</h3><div class="empty-state">Sem dados</div></section>'
            else: body=f'<div class="{cls}" id="{cid}">{label}</div>'
            parts.append(body)
        mode=html.escape(str(theme.get('mode','light'))); layout=html.escape(str(theme.get('layout','single')))
        return '<!doctype html><html><head><meta charset="utf-8"><title>Aurora Preview</title><style>body{font-family:system-ui;margin:24px}.app-layout{display:grid;gap:16px}.preview-component,.app-sidebar{padding:16px;border:1px solid #ccc;border-radius:8px}button{padding:8px 14px}.empty-state{opacity:.65}</style></head><body data-theme="'+mode+'" data-layout="'+layout+'"><main class="app-layout">'+''.join(parts)+'</main></body></html>'
    def write_preview(self, app_path, filename='.aurora-preview.html'):
        app=self._app(app_path); p=app/'frontend'/filename
        p.write_text(self.render(app),encoding='utf-8'); return {'path':str(p),'bytes':p.stat().st_size}
