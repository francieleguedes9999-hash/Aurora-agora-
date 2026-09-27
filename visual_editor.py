from __future__ import annotations
import json, re, hashlib
from pathlib import Path

class VisualEditor:
    """Visual editor with previews, component targeting and persistent undo/redo."""
    def __init__(self, workspace):
        self.root = Path(workspace).resolve()

    def _app(self, app_path):
        p = Path(app_path)
        if not p.is_absolute(): p = self.root / p
        p = p.resolve()
        if not (p == self.root or self.root in p.parents): raise ValueError('app fora do workspace')
        return p

    def _state_path(self, app): return app / 'frontend' / '.aurora_visual_history.json'

    def load(self, app_path):
        app = self._app(app_path); path = app / 'frontend' / 'ui.json'
        if not path.exists(): raise FileNotFoundError('frontend/ui.json não encontrado')
        return app, path, json.loads(path.read_text(encoding='utf-8'))

    def _state(self, app):
        p=self._state_path(app)
        if not p.exists(): return {'past': [], 'future': []}
        try: return json.loads(p.read_text(encoding='utf-8'))
        except Exception: return {'past': [], 'future': []}

    def _save_state(self, app, state):
        p=self._state_path(app); p.write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    def _push(self, app, ui):
        state=self._state(app); state['past'].append(ui); state['past']=state['past'][-20:]; state['future']=[]; self._save_state(app,state)

    def preview(self, app_path, instruction):
        app, _, ui = self.load(app_path)
        candidate = json.loads(json.dumps(ui))
        changes = self._mutate(candidate, instruction)
        return {'ok': True, 'preview': True, 'changes': changes, 'before': ui, 'after': candidate, 'fingerprint': self._fingerprint(candidate)}

    def apply(self, app_path, instruction):
        app, path, ui = self.load(app_path)
        candidate=json.loads(json.dumps(ui)); changes=self._mutate(candidate,instruction)
        if not changes: return {'ok': True, 'changes': [], 'ui': ui, 'fingerprint': self._fingerprint(ui)}
        self._push(app, ui)
        path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        self._sync_css(app,candidate)
        return {'ok': True, 'changes': changes, 'ui': candidate, 'fingerprint': self._fingerprint(candidate)}

    def undo(self, app_path):
        app,path,ui=self.load(app_path); state=self._state(app)
        if not state['past']: return {'ok': False, 'error':'não há alteração para desfazer'}
        state['future'].append(ui); previous=state['past'].pop(); path.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); self._sync_css(app,previous); self._save_state(app,state)
        return {'ok':True,'ui':previous,'fingerprint':self._fingerprint(previous)}

    def redo(self, app_path):
        app,path,ui=self.load(app_path); state=self._state(app)
        if not state['future']: return {'ok': False, 'error':'não há alteração para refazer'}
        state['past'].append(ui); nxt=state['future'].pop(); path.write_text(json.dumps(nxt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); self._sync_css(app,nxt); self._save_state(app,state)
        return {'ok':True,'ui':nxt,'fingerprint':self._fingerprint(nxt)}

    def inspect_component(self, app_path, component_id):
        """Return a normalized editable view of one visual component."""
        _, _, ui = self.load(app_path)
        comp = next((c for c in ui.get("components", []) if c.get("id") == component_id), None)
        if comp is None:
            return {"ok": False, "error": "componente não encontrado", "component_id": component_id}
        props = dict(comp.get("props", {}))
        return {"ok": True, "component": {
            "id": comp.get("id"), "type": comp.get("type", "unknown"),
            "label": comp.get("label"), "props": props},
            "editable": {"text": True, "size": True, "position": True, "style": True, "behavior": True}}

    def set_properties(self, app_path, component_id, properties, preview=False):
        """Set structured component properties instead of relying only on natural-language parsing."""
        app, path, ui = self.load(app_path)
        comp = next((c for c in ui.get("components", []) if c.get("id") == component_id), None)
        if comp is None:
            return {"ok": False, "error": "componente não encontrado", "component_id": component_id}
        candidate = json.loads(json.dumps(ui))
        target = next(c for c in candidate.get("components", []) if c.get("id") == component_id)
        old = json.loads(json.dumps(target))
        target.setdefault("props", {})
        allowed = {"text","width","height","min_width","max_width","x","y","gap","padding","margin","align","justify","color","background","border","radius","font_size","font_weight","hidden","disabled","action","href","placeholder","required","columns","variant"}
        for key, value in (properties or {}).items():
            if key not in allowed:
                raise ValueError(f"propriedade visual não permitida: {key}")
            target["props"][key] = value
        if "text" in (properties or {}): target["label"] = str(properties["text"])
        changes = []
        if target != old: changes.append({"component_id": component_id, "before": old, "after": target})
        if preview:
            return {"ok": True, "preview": True, "changes": changes, "component": target, "fingerprint": self._fingerprint(candidate)}
        if not changes:
            return {"ok": True, "changes": [], "component": target, "fingerprint": self._fingerprint(ui)}
        self._push(app, ui)
        path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        self._sync_css(app, candidate)
        return {"ok": True, "changes": changes, "component": target, "fingerprint": self._fingerprint(candidate)}

    def _mutate(self, ui, instruction):
        text=(instruction or '').strip(); low=text.lower(); components=ui.setdefault('components',[]); theme=ui.setdefault('theme',{}); changes=[]
        target=None
        m=re.search(r'(?:componente|component)\s+["\']?([\w-]+)',low)
        if m: target=m.group(1)
        if 'preview' in low and len(low.split())<=2: return []
        if any(x in low for x in ('menu lateral','sidebar','barra lateral')):
            components[:]=[c for c in components if c.get('type')!='sidebar']; components.insert(0,{'id':'main-sidebar','type':'sidebar','label':'Menu','props':{'position':'left'}}); theme['navigation']='sidebar'; changes.append('navigation=sidebar')
        if any(x in low for x in ('duas colunas','2 colunas','duas-colunas','two columns')): theme['layout']='two-column'; changes.append('layout=two-column')
        if any(x in low for x in ('três colunas','3 colunas','three columns')): theme['layout']='three-column'; changes.append('layout=three-column')
        if 'botão' in low and any(x in low for x in ('novo','adicionar','criar')) and not any(c.get('id')=='new-record-button' for c in components): components.append({'id':'new-record-button','type':'button','label':'Novo','props':{'action':'create'}}); changes.append('button=Novo')
        m2=re.search(r'(?:tema|theme).{0,20}(?:escuro|dark|claro|light)',low)
        if m2: theme['mode']='dark' if ('escuro' in m2.group(0) or 'dark' in m2.group(0)) else 'light'; changes.append('theme mode')
        if any(x in low for x in ('compacto','compact')): theme['density']='compact'; changes.append('density=compact')
        if any(x in low for x in ('confortável','confortavel','comfortable')): theme['density']='comfortable'; changes.append('density=comfortable')
        if target:
            comp=next((c for c in components if c.get('id')==target),None)
            if comp and any(x in low for x in ('oculte','ocultar','hide')): comp['props']=dict(comp.get('props',{}),hidden=True); changes.append(f'{target}=hidden')
            if comp and any(x in low for x in ('mostre','mostrar','show')): comp.setdefault('props',{}).pop('hidden',None); changes.append(f'{target}=visible')
            if comp and 'texto' in low:
                mm=re.search(r'texto\s+(?:para|:)?\s*["\']?(.+?)["\']?$',text,re.I)
                if mm: comp['label']=mm.group(1).strip(' "\''); changes.append(f'{target}=label')
        return changes

    def _fingerprint(self, ui): return hashlib.sha256(json.dumps(ui,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12]

    def _sync_css(self, app, ui):
        css_path=app/'frontend'/'styles.css'; css=css_path.read_text(encoding='utf-8') if css_path.exists() else ''; marker='/* Aurora visual editor */'; block=f"\n{marker}\n.app-layout{{display:grid;gap:1rem}}\n"; layout=ui.get('theme',{}).get('layout')
        if layout=='two-column': block+='@media(min-width:800px){.app-layout{grid-template-columns:1fr 1fr}}\n'
        elif layout=='three-column': block+='@media(min-width:1000px){.app-layout{grid-template-columns:repeat(3,1fr)}}\n'
        else: block+='@media(min-width:800px){.app-layout{grid-template-columns:1fr}}\n'
        if ui.get('theme',{}).get('navigation')=='sidebar': block+='.app-sidebar{grid-column:1}\n'
        if marker in css: css=css.split(marker)[0].rstrip()+block
        else: css=css.rstrip()+block
        css_path.write_text(css+'\n',encoding='utf-8')
