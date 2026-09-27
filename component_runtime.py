from __future__ import annotations

from dataclasses import asdict
from typing import Any

SMART_TYPES = {
    'button': {'capabilities': ['action']},
    'form': {'capabilities': ['submit', 'fields', 'validation']},
    'entity-form': {'capabilities': ['submit', 'fields', 'validation', 'api']},
    'data-list': {'capabilities': ['api', 'search', 'sort', 'pagination', 'refresh']},
    'toolbar': {'capabilities': ['actions', 'search', 'refresh']},
    'header': {'capabilities': ['navigation', 'title']},
    'sidebar': {'capabilities': ['navigation']},
    'content': {'capabilities': ['content']},
}

class ComponentRuntime:
    """Turns visual component declarations into a validated behavioral contract."""
    def normalize(self, components: list[dict[str, Any]] | list[Any]) -> list[dict[str, Any]]:
        out=[]
        for raw in components or []:
            item = asdict(raw) if hasattr(raw, '__dataclass_fields__') else dict(raw)
            ctype=str(item.get('type','content'))
            meta=SMART_TYPES.get(ctype, {'capabilities': []})
            props=dict(item.get('props') or {})
            behavior=dict(props.get('behavior') or {})
            if ctype in {'entity-form','data-list'}:
                behavior.setdefault('api', True)
            if ctype == 'data-list':
                behavior.setdefault('refresh', True)
                behavior.setdefault('search', bool(props.get('search', True)))
                behavior.setdefault('pagination', bool(props.get('pagination', True)))
            if ctype in {'form','entity-form'}:
                behavior.setdefault('submit', True)
                behavior.setdefault('validation', True)
            props['behavior']=behavior
            item['props']=props
            item['capabilities']=list(meta['capabilities'])
            out.append(item)
        return out

    def inspect(self, components, component_id: str) -> dict[str, Any]:
        normalized=self.normalize(components)
        item=next((x for x in normalized if x.get('id')==component_id), None)
        if item is None:
            return {'ok':False,'error':'componente não encontrado','component_id':component_id}
        return {'ok':True,'component':item}

    def validate(self, components) -> dict[str, Any]:
        normalized=self.normalize(components)
        ids=[x.get('id') for x in normalized]
        duplicate=sorted({x for x in ids if ids.count(x)>1 and x})
        errors=[]
        if duplicate: errors.append({'type':'duplicate_id','ids':duplicate})
        for c in normalized:
            if not c.get('id'): errors.append({'type':'missing_id','component':c})
            if not c.get('type'): errors.append({'type':'missing_type','component':c})
        return {'ok':not errors,'errors':errors,'components':normalized}
