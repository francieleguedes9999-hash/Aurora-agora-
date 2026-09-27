from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class VisualWorkflow:
    """Visual graph representation for declarative workflows.

    The graph is a projection of a workflow definition: nodes are steps and
    edges are explicit transitions. It never executes workflow code.
    """
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.path = self.root / '.aurora' / 'workflow_visuals.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    @staticmethod
    def from_workflow(workflow: dict[str, Any]) -> dict[str, Any]:
        steps = workflow.get('steps') or []
        nodes = []
        edges = []
        for i, step in enumerate(steps):
            sid = str(step.get('id', ''))
            stype = str(step.get('type', 'action'))
            nodes.append({
                'id': sid, 'type': stype,
                'label': step.get('label') or step.get('action') or sid,
                'x': int(step.get('x', (i % 4) * 240)),
                'y': int(step.get('y', (i // 4) * 140)),
            })
            for field, kind in (('next', 'next'), ('then', 'true'), ('else', 'false'), ('on_error', 'error')):
                target = step.get(field)
                if target:
                    edges.append({'from': sid, 'to': str(target), 'kind': kind})
        return {'version': 1, 'workflow_id': workflow.get('id'), 'name': workflow.get('name', ''), 'nodes': nodes, 'edges': edges}

    def save(self, workflow_id: str, graph: dict[str, Any]) -> dict[str, Any]:
        graph = dict(graph)
        graph['workflow_id'] = workflow_id
        graph.setdefault('version', 1)
        graph.setdefault('nodes', [])
        graph.setdefault('edges', [])
        check = self.validate(graph)
        if not check['ok']:
            return check
        self.data[workflow_id] = graph
        self._save()
        return {'ok': True, 'graph': graph}

    def get(self, workflow_id: str) -> dict[str, Any]:
        graph = self.data.get(workflow_id)
        return {'ok': bool(graph), 'graph': graph} if graph else {'ok': False, 'error': 'grafo não encontrado'}

    def validate(self, graph: dict[str, Any]) -> dict[str, Any]:
        errors = []
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])
        if not isinstance(nodes, list): errors.append({'type': 'invalid_nodes'})
        if not isinstance(edges, list): errors.append({'type': 'invalid_edges'})
        ids = [str(n.get('id', '')) for n in nodes if isinstance(n, dict)]
        if any(not x for x in ids): errors.append({'type': 'missing_node_id'})
        if len(ids) != len(set(ids)): errors.append({'type': 'duplicate_node_id'})
        known = set(ids)
        for edge in edges if isinstance(edges, list) else []:
            if not isinstance(edge, dict): errors.append({'type': 'invalid_edge'}); continue
            if edge.get('from') not in known or edge.get('to') not in known:
                errors.append({'type': 'missing_edge_target', 'edge': edge})
        return {'ok': not errors, 'errors': errors}

    def update_node(self, workflow_id: str, node_id: str, props: dict[str, Any]) -> dict[str, Any]:
        graph = self.data.get(workflow_id)
        if not graph: return {'ok': False, 'error': 'grafo não encontrado'}
        for node in graph.get('nodes', []):
            if node.get('id') == node_id:
                allowed = {'label','x','y','width','height','collapsed'}
                for key, value in props.items():
                    if key in allowed: node[key] = value
                check = self.validate(graph)
                if not check['ok']: return check
                self._save(); return {'ok': True, 'graph': graph, 'node': node}
        return {'ok': False, 'error': 'nó não encontrado'}

    def to_html(self, workflow_id: str) -> str:
        result = self.get(workflow_id)
        if not result['ok']: return '<p>Workflow não encontrado</p>'
        graph = result['graph']
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])
        lines = ['<div class="aurora-workflow-canvas">']
        lines.append('<svg class="aurora-workflow-edges" aria-hidden="true">')
        by_id = {n['id']: n for n in nodes}
        for edge in edges:
            a, b = by_id.get(edge['from']), by_id.get(edge['to'])
            if not a or not b: continue
            x1, y1 = int(a.get('x', 0))+100, int(a.get('y', 0))+45
            x2, y2 = int(b.get('x', 0)), int(b.get('y', 0))+45
            lines.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" data-kind="{edge.get("kind", "next")}"/>')
        lines.append('</svg>')
        for node in nodes:
            lines.append(f'<div class="aurora-workflow-node" data-node-id="{node["id"]}" style="left:{int(node.get("x",0))}px;top:{int(node.get("y",0))}px">{node.get("label", node["id"])}</div>')
        lines.append('</div>')
        return ''.join(lines)
