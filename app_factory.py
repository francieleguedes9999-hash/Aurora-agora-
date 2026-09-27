import json
from dataclasses import dataclass, asdict
from pathlib import Path
from html import escape
from urllib.parse import urlparse, parse_qs, quote

from .component_runtime import ComponentRuntime


@dataclass
class AppSpec:
    name: str
    kind: str = 'web'
    frontend: str = 'html'
    backend: str = 'python'
    database: str = 'sqlite'
    auth: bool = False
    description: str = ''

class AppFactory:
    """Generates small, runnable application prototypes from an AppSpec."""
    def __init__(self, workspace):
        self.root = Path(workspace).resolve()
        self.output_root = self.root / 'apps'
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.component_runtime = ComponentRuntime()

    def _safe_name(self, name):
        value = ''.join(c.lower() if c.isalnum() else '-' for c in name).strip('-')
        if not value:
            raise ValueError('nome do aplicativo inválido')
        return value

    def _files(self, spec):
        desc = spec.description or f'{spec.name} application'
        title = escape(spec.name)
        files = {
            'README.md': f'''# {spec.name}\n\n{desc}\n\nGerado pela Aurora App Factory.\n\n## Executar\n\n```bash\npython backend/main.py\n```\n\nAbra http://127.0.0.1:8000/ no navegador.\n''',
            'aurora.app.json': json.dumps(asdict(spec), ensure_ascii=False, indent=2) + '\n',
            'frontend/ui.json': json.dumps({'theme': getattr(spec, 'theme', {}), 'components': [asdict(c) for c in getattr(spec, 'components', [])]}, ensure_ascii=False, indent=2) + '\n',
            '.gitignore': '__pycache__/\n.venv/\n.env\nnode_modules/\n*.db\n',
            'backend/__init__.py': '',
            'backend/main.py': self._backend(spec),
            'tests/test_generated_app.py': self._generated_tests(spec),
        }
        if spec.kind in {'web', 'fullstack'}:
            files.update({
                'frontend/index.html': f"""<!doctype html>
<html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{title}</title><link rel=\"stylesheet\" href=\"styles.css\"></head>
<body><header><h1>{title}</h1><p id=\"description\">{escape(desc)}</p></header>
<main><div id=\"screen-shell\" class=\"screen-shell\"></div>
<section id=\"auth\" class=\"card\"><h2>Login</h2><form id=\"login-form\"><label>E-mail<input id=\"email\" type=\"email\" required></label><label>Senha<input id=\"password\" type=\"password\" required></label><button type=\"submit\">Entrar</button></form><div id=\"auth-status\" role=\"status\"></div></section>
<section id=\"app\" class=\"card\" hidden><div class=\"toolbar\"><h2>Dados</h2><button id=\"refresh\">Atualizar</button><span id=\"loading\" aria-live=\"polite\" hidden>Carregando...</span></div><div id=\"error\" class=\"error\" role=\"alert\" hidden></div><div id=\"forms\"></div><div id=\"data\"></div></section>
</main><script src=\"app.js\"></script></body></html>
""",
                'frontend/app.js': self._frontend_js(spec),
                'frontend/styles.css': """* { box-sizing:border-box } body { font-family: system-ui, sans-serif; max-width: 1180px; margin: 0 auto; padding: 1rem; background: #f6f7f9; color: #1f2937; line-height:1.5 } header { padding: .5rem 0 1rem } .card { background: white; border: 1px solid #ddd; border-radius: 12px; padding: 1rem; margin: 1rem 0; box-shadow:0 2px 8px rgba(0,0,0,.04) } form { display:grid; gap:.7rem; max-width:520px } label { display:grid; gap:.25rem; font-weight:600 } input,select { padding:.65rem; border:1px solid #bbb; border-radius:8px; min-height:42px } button { padding:.65rem 1rem; border:0; border-radius:8px; cursor:pointer; background:#1f2937; color:white } button:disabled { opacity:.55; cursor:not-allowed } button:focus-visible,input:focus-visible,select:focus-visible { outline:3px solid #93c5fd; outline-offset:2px } .smart-nav{display:flex;gap:.5rem;flex-wrap:wrap;margin:1rem 0}.screen-shell{margin:1rem 0}.screen-card{border:1px solid #e5e7eb;border-radius:10px;padding:1rem;background:#fff}.screen-card[data-active=\"true\"]{outline:3px solid #93c5fd}.smart-nav button{background:#374151}.toolbar { display:flex; gap:1rem; align-items:center; flex-wrap:wrap } .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:1rem } .error { padding:.7rem; margin:.7rem 0; border-radius:8px; background:#fee2e2 } .ok { padding:.7rem; margin:.7rem 0; border-radius:8px; background:#dcfce7 } table { width:100%; border-collapse:collapse; margin-top:1rem; display:block; overflow:auto } th,td { padding:.55rem; border-bottom:1px solid #ddd; text-align:left; white-space:nowrap } .entity-form { margin:1rem 0; padding:1rem; border:1px solid #eee; border-radius:10px; background:#fafafa } .empty { padding:1rem; border:1px dashed #bbb; border-radius:10px; text-align:center } #loading[hidden], #error[hidden] { display:none } @media (max-width:640px) { body{padding:.7rem} .card{padding:.8rem} .toolbar > *{width:100%} button{width:100%} }""",
            })
        # Standalone browser preview: no backend, network, or login required.
        files['preview/index.html'] = self._preview_html(spec)
        files['preview/README.md'] = 'Abra index.html no navegador. Este preview é local e usa dados fictícios.\n'
        files['preview/preview.json'] = json.dumps({
            'name': spec.name,
            'description': desc,
            'entities': [asdict(e) for e in getattr(spec, 'entities', [])],
            'components': self.component_runtime.normalize(getattr(spec, 'components', [])),
            'screens': [asdict(x) for x in getattr(spec, 'screens', [])],
            'theme': getattr(spec, 'theme', {}),
        }, ensure_ascii=False, indent=2) + '\n'
        if spec.database != 'none':
            files['database/schema.sql'] = self._schema(spec)
            files['database/relationships.json'] = json.dumps(self._relationships(spec), ensure_ascii=False, indent=2) + '\n'
            files['database/migrations/001_initial.sql'] = self._schema(spec)
            files['database/migrate.py'] = '''import sqlite3\nfrom pathlib import Path\n\nROOT=Path(__file__).resolve().parents[1]\nDB=ROOT/'database'/'app.db'\nMIGRATIONS=ROOT/'database'/'migrations'\n\ndef migrate():\n    DB.parent.mkdir(parents=True, exist_ok=True)\n    with sqlite3.connect(DB) as db:\n        db.execute('CREATE TABLE IF NOT EXISTS _aurora_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')\n        for path in sorted(MIGRATIONS.glob('*.sql')):\n            version=int(path.stem.split('_',1)[0])\n            if not db.execute('SELECT 1 FROM _aurora_migrations WHERE version=?',(version,)).fetchone():\n                db.executescript(path.read_text(encoding='utf-8'))\n                db.execute('INSERT INTO _aurora_migrations(version) VALUES (?)',(version,))\n        db.commit()\n\nif __name__=='__main__': migrate()\n'''
            files['database/db.py'] = '''import sqlite3\nfrom pathlib import Path\n\ndef connect(path=None):\n    path = path or Path(__file__).with_name('app.db')\n    db=sqlite3.connect(path)\n    db.execute('PRAGMA foreign_keys=ON')\n    return db\n'''
        if spec.auth:
            files['backend/auth.py'] = '''def authenticate(token):\n    """Minimal prototype authentication boundary; replace with real identity provider in production."""\n    return bool(token)\n'''
        if spec.kind == 'mobile':
            files['mobile/README.md'] = f'# {spec.name} mobile app\n\nMobile client boundary generated by Aurora.\n'
            files['mobile/api_client.js'] = "export async function health(baseUrl) { const r = await fetch(`${baseUrl}/api/health`); return r.json(); }\n"
        if spec.kind == 'api':
            files['backend/api.py'] = 'def health():\n    return {"status": "ok"}\n'
        return files

    def _preview_html(self, spec):
        title = escape(spec.name)
        desc = escape(spec.description or f'{spec.name} application')
        entities = getattr(spec, 'entities', [])
        entity_json = json.dumps([{'name': e.name, 'fields': list(e.fields)} for e in entities], ensure_ascii=False)
        return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - Preview Aurora</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,sans-serif;background:#f5f7fb;color:#172033}}header{{padding:24px 28px;background:#fff;border-bottom:1px solid #e5e7eb}}header h1{{margin:0 0 6px}}main{{max-width:1180px;margin:auto;padding:24px}}.nav{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}}button{{border:0;border-radius:8px;padding:10px 14px;cursor:pointer;background:#172033;color:#fff}}button.secondary{{background:#e5e7eb;color:#172033}}.card{{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.04)}}.field{{display:grid;gap:5px;margin:9px 0}}input{{padding:9px;border:1px solid #cbd5e1;border-radius:7px}}table{{width:100%;border-collapse:collapse;margin-top:12px}}th,td{{padding:9px;border-bottom:1px solid #e5e7eb;text-align:left}}.badge{{display:inline-block;padding:4px 8px;border-radius:999px;background:#e0f2fe;font-size:12px}}#toast{{position:fixed;right:18px;bottom:18px;background:#172033;color:#fff;padding:12px 16px;border-radius:9px;display:none}}
</style></head><body>
<header><span class="badge">Preview local da Aurora</span><h1>{title}</h1><p>{desc}</p></header>
<main><div id="nav" class="nav"></div><section id="content"></section></main><div id="toast"></div>
<script>
const ENTITIES={entity_json};
const state={{active:ENTITIES[0]?.name||'Resumo',rows:Object.fromEntries(ENTITIES.map(e=>[e.name,[]]))}};
function toast(m){{const t=document.querySelector('#toast');t.textContent=m;t.style.display='block';setTimeout(()=>t.style.display='none',1600)}}
function sampleRows(e){{return Array.from({{length:3}},(_,i)=>Object.fromEntries(e.fields.filter(f=>f!=='id').map(f=>[f,`${{f}} ${{i+1}}`])));}}
function renderNav(){{const n=document.querySelector('#nav');n.innerHTML='';for(const e of ENTITIES){{const b=document.createElement('button');b.textContent=e.name;b.onclick=()=>{{state.active=e.name;render()}};n.appendChild(b)}}}}
function render(){{renderNav();const root=document.querySelector('#content');root.innerHTML='';const e=ENTITIES.find(x=>x.name===state.active);if(!e){{root.innerHTML='<article class="card"><h2>Preview gerado</h2><p>O aplicativo foi gerado com sucesso.</p></article>';return}}const card=document.createElement('article');card.className='card';card.innerHTML=`<h2>${{e.name}}</h2><p>Dados simulados para visualização.</p>`;const form=document.createElement('div');for(const f of e.fields.filter(f=>f!=='id')){{const label=document.createElement('label');label.className='field';label.innerHTML=`<span>${{f}}</span><input data-field="${{f}}" placeholder="${{f}}">`;form.appendChild(label)}}const add=document.createElement('button');add.textContent='Adicionar';add.onclick=()=>{{const row={{}};form.querySelectorAll('input').forEach(i=>row[i.dataset.field]=i.value||'(vazio)');state.rows[e.name].push(row);toast('Registro adicionado ao preview');render()}};form.appendChild(add);card.appendChild(form);const rows=state.rows[e.name].length?state.rows[e.name]:sampleRows(e);const table=document.createElement('table');table.innerHTML='<thead><tr>'+e.fields.map(f=>`<th>${{f}}</th>`).join('')+'</tr></thead><tbody>'+rows.map((r,i)=>'<tr>'+e.fields.map(f=>`<td>${{f==='id'?i+1:r[f]??''}}</td>`).join('')+'</tr>').join('')+'</tbody>';card.appendChild(table);root.appendChild(card)}}
render();
</script></body></html>"""

    def _frontend_js(self, spec):
        import json as _json
        entities = [{'name': e.name, 'fields': list(e.fields)} for e in getattr(spec, 'entities', [])]
        components = self.component_runtime.normalize(getattr(spec, 'components', []))
        screens = [asdict(x) for x in getattr(spec, 'screens', [])]
        contract = _json.dumps({'entities': entities, 'components': components, 'screens': screens}, ensure_ascii=False)
        return """const CONTRACT = %s;
const $ = (s) => document.querySelector(s);
const state = { token: localStorage.getItem('aurora_token') || '', loading: false, data: {}, page: {}, pageSize: 10, query: {} };
function setLoading(value) { state.loading = value; $('#loading').hidden = !value; $('#refresh').disabled = value; }
function showError(message) { const el=$('#error'); el.textContent=message || ''; el.hidden=!message; }
function showAuth(message, ok=false) { const el=$('#auth-status'); el.textContent=message || ''; el.className=ok?'ok':''; }
async function api(path, options={}) {
  const headers={'Content-Type':'application/json', ...(options.headers||{})};
  if (state.token) headers.Authorization=`Bearer ${state.token}`;
  const response=await fetch(path, {...options, headers});
  let body=null; try { body=await response.json(); } catch { body={}; }
  if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
  return body;
}
function slug(name) { return name.toLowerCase().replace(/[^a-z0-9À-ÿ]+/g,'-').replace(/^-|-$/g,''); }
function editableFields(entity) { return entity.fields.filter(f=>f!=='id'); }
function validatePayload(entity, payload) { for (const field of editableFields(entity)) { if (!String(payload[field] ?? '').trim()) throw new Error(`${field} é obrigatório`); } }
function pageRows(entity, rows) { const page=state.page[entity.name]||1; const start=(page-1)*state.pageSize; return rows.slice(start,start+state.pageSize); }
function componentByType(type) { return (CONTRACT.components||[]).filter(c=>c.type===type); }
const SCREEN_ENTITY_HINTS = { catalog:'Product', product:'Product', tasks:'Task', calendar:'Event', dashboard:null };
function screenEntity(screen) {
  const hinted = SCREEN_ENTITY_HINTS[screen.id];
  if (hinted && CONTRACT.entities.some(e=>e.name===hinted)) return CONTRACT.entities.find(e=>e.name===hinted);
  if (CONTRACT.entities.length===1) return CONTRACT.entities[0];
  return null;
}
function renderScreenContent(screen, workspace) {
  const entity = screenEntity(screen);
  const id = screen.id || '';
  workspace.innerHTML='';
  const h=document.createElement('h3'); h.textContent=screen.name || screen.id; workspace.appendChild(h);
  const p=document.createElement('p'); p.textContent=screen.purpose || 'Tela do aplicativo'; workspace.appendChild(p);
  if (id==='login') {
    const form=document.createElement('form'); form.className='entity-form';
    for (const field of ['email','password']) { const label=document.createElement('label'); label.textContent=field==='email'?'E-mail':'Senha'; const input=document.createElement('input'); input.type=field==='password'?'password':'email'; input.required=true; input.name=field; label.appendChild(input); form.appendChild(label); }
    const b=document.createElement('button'); b.type='button'; b.textContent='Entrar'; b.onclick=()=>showAuth('Login pronto para integração',true); form.appendChild(b); workspace.appendChild(form); return;
  }
  if (!entity) { const empty=document.createElement('div'); empty.className='empty'; empty.textContent='Esta tela ainda não possui uma entidade de dados associada.'; workspace.appendChild(empty); return; }
  const title=document.createElement('h4'); title.textContent=`Dados: ${entity.name}`; workspace.appendChild(title);
  const rows=state.data[entity.name] || [];
  if (!rows.length) { const empty=document.createElement('div'); empty.className='empty'; empty.textContent=`Nenhum ${entity.name} carregado. Use o formulário abaixo para criar um registro.`; workspace.appendChild(empty); }
  else { const table=document.createElement('table'); const cols=entity.fields; table.innerHTML='<thead><tr>'+cols.map(f=>`<th>${f}</th>`).join('')+'</tr></thead><tbody>'+rows.slice(0,10).map((r,i)=>'<tr>'+cols.map(f=>`<td>${r[f] ?? (f==='id'?i+1:'')}</td>`).join('')+'</tr>').join('')+'</tbody>'; workspace.appendChild(table); }
  if (id!=='product' && id!=='dashboard') { const note=document.createElement('p'); note.textContent='A tela está vinculada à entidade e ao fluxo de dados correspondente.'; workspace.appendChild(note); }
}
function renderScreenShell() {
  const root = $('#screen-shell'); if (!root) return; root.innerHTML='';
  const screens = CONTRACT.screens || [];
  if (!screens.length) return;
  const title = document.createElement('h2'); title.textContent='Telas do aplicativo'; root.appendChild(title);
  const workspace = document.createElement('section'); workspace.className='screen-workspace'; workspace.setAttribute('aria-live','polite');
  const grid = document.createElement('div'); grid.className='grid';
  const activate = (screen, card) => {
    document.querySelectorAll('.screen-card').forEach(x=>x.removeAttribute('data-active'));
    card.dataset.active='true';
    const route = screen.route || '/';
    history.replaceState({route}, '', `#${route.split('/').filter(Boolean).join('/')}`);
    workspace.innerHTML='';
    renderScreenContent(screen, workspace);
    const meta=document.createElement('code'); meta.textContent=route;
    workspace.appendChild(meta);
    const actions=document.createElement('div'); actions.className='toolbar';
    const info=document.createElement('span'); info.textContent=`Tela ativa: ${screen.name || screen.id}`;
    const back=document.createElement('button'); back.type='button'; back.textContent='Fechar'; back.onclick=()=>{workspace.innerHTML='<p class="empty">Selecione uma tela para começar.</p>'; document.querySelectorAll('.screen-card').forEach(x=>x.removeAttribute('data-active')); history.replaceState({},'',location.pathname+location.search);};
    actions.append(info,back); workspace.append(h,p,meta,actions);
    showAuth(`Tela aberta: ${screen.name || screen.id}`, true);
  };
  screens.forEach((screen, index)=>{
    const card=document.createElement('article'); card.className='screen-card'; card.dataset.screen=screen.id || index;
    const h=document.createElement('h3'); h.textContent=screen.name || screen.id;
    const p=document.createElement('p'); p.textContent=screen.purpose || '';
    const route=document.createElement('code'); route.textContent=screen.route || '/';
    const button=document.createElement('button'); button.type='button'; button.textContent='Abrir tela';
    button.onclick=()=>activate(screen, card);
    card.append(h,p,route,button); grid.appendChild(card);
  });
  root.append(grid, workspace);
  const initial = location.hash ? screens.find(x=>`#${(x.route||'/').split('/').filter(Boolean).join('/')}`===location.hash) : null;
  if (initial) { const cards=[...grid.querySelectorAll('.screen-card')]; activate(initial, cards[screens.indexOf(initial)]); }
  else workspace.innerHTML='<p class="empty">Selecione uma tela para começar.</p>';
}
function renderSmartNavigation() {
  const nav=document.querySelector('nav[data-aurora-smart]'); if(!nav) return;
  nav.innerHTML='';
  for(const c of componentByType('sidebar').concat(componentByType('header'))) {
    const item=document.createElement('button'); item.type='button'; item.textContent=c.label||c.props?.text||c.id;
    item.onclick=()=>showAuth(`Componente ${c.id} selecionado`, true); nav.appendChild(item);
  }
}
function smartComponentStatus() {
  const lists=componentByType('data-list'); const forms=componentByType('entity-form').concat(componentByType('form'));
  return {lists:lists.length, forms:forms.length, apiBound:lists.length+forms.length};
}
function renderForms() {
  renderScreenShell();
  const root=$('#forms'); root.innerHTML='';
  renderSmartNavigation();
  for (const entity of CONTRACT.entities) {
    const box=document.createElement('div'); box.className='entity-form';
    const form=document.createElement('form'); form.dataset.entity=entity.name;
    const title=document.createElement('h3'); title.textContent=`Novo ${entity.name}`; box.appendChild(title);
    for (const field of editableFields(entity)) {
      const label=document.createElement('label'); label.textContent=field;
      const input=document.createElement('input'); input.name=field; input.required=true; label.appendChild(input); form.appendChild(label);
    }
    const button=document.createElement('button'); button.type='submit'; button.textContent='Salvar'; form.appendChild(button);
    form.addEventListener('submit', async (event)=>{ event.preventDefault(); await createEntity(entity, form); });
    box.appendChild(form); root.appendChild(box);
  }
}
async function createEntity(entity, form) {
  showError(''); setLoading(true);
  try {
    const payload=Object.fromEntries(new FormData(form).entries());
    validatePayload(entity, payload);
    const result=await api(`/api/${slug(entity.name)}s`, {method:'POST', body:JSON.stringify(payload)});
    form.reset(); await loadEntity(entity); showAuth(`${entity.name} salvo com sucesso`, true); return result;
  } catch (error) { showError(error.message); } finally { setLoading(false); }
}
async function loadEntity(entity) {
  const q=state.query?.[entity.name] || {search:'',sort:'id',order:'desc'};
  const params=new URLSearchParams({page:'1',limit:'1000'}); if(q.search) params.set('search',q.search); if(q.sort) params.set('sort',q.sort); if(q.order) params.set('order',q.order);
  const rows=await api(`/api/${slug(entity.name)}s?${params.toString()}`); state.data[entity.name]=Array.isArray(rows)?rows:(rows.items||[]); if (!state.page[entity.name]) state.page[entity.name]=1; renderData();
}
async function updateEntity(entity, id, payload) { validatePayload(entity,payload); return api(`/api/${slug(entity.name)}s/${id}`, {method:'PUT', body:JSON.stringify(payload)}); }
async function deleteEntity(entity, id) { return api(`/api/${slug(entity.name)}s/${id}`, {method:'DELETE'}); }
async function editRow(entity, row) { const payload={}; for (const field of editableFields(entity)) { const value=window.prompt(`Novo ${field}:`, row[field] ?? ''); if (value===null) return; payload[field]=value; } showError(''); setLoading(true); try { await updateEntity(entity,row.id,payload); await loadEntity(entity); showAuth(`${entity.name} atualizado`,true); } catch(error){ showError(error.message); } finally { setLoading(false); } }
async function removeRow(entity,row){ if(!window.confirm(`Excluir ${entity.name} #${row.id}?`)) return; showError(''); setLoading(true); try { await deleteEntity(entity,row.id); const rows=state.data[entity.name]||[]; if((state.page[entity.name]||1)>1 && rows.length-1 <= ((state.page[entity.name]||1)-1)*state.pageSize) state.page[entity.name]--; await loadEntity(entity); showAuth(`${entity.name} excluído`,true); } catch(error){ showError(error.message); } finally { setLoading(false); } }
function renderData() {
  const root=$('#data'); root.innerHTML='';
  for (const entity of CONTRACT.entities) {
    const rows=state.data[entity.name] || []; const section=document.createElement('section');
    const heading=document.createElement('h3'); heading.textContent=entity.name; section.appendChild(heading);
    if (!rows.length) { const p=document.createElement('p'); p.textContent='Nenhum registro encontrado. Crie o primeiro usando o formulário acima.'; section.appendChild(p); root.appendChild(section); continue; }
    const controlsTop=document.createElement('div'); controlsTop.className='toolbar';
    const search=document.createElement('input'); search.placeholder='Buscar...'; search.value=(state.query[entity.name]||{}).search||'';
    const sort=document.createElement('select'); for(const f of entity.fields){const o=document.createElement('option');o.value=f;o.textContent=`Ordenar: ${f}`;sort.appendChild(o);} sort.value=(state.query[entity.name]||{}).sort||'id';
    const order=document.createElement('select'); [['desc','↓'],['asc','↑']].forEach(([v,t])=>{const o=document.createElement('option');o.value=v;o.textContent=t;order.appendChild(o);}); order.value=(state.query[entity.name]||{}).order||'desc';
    const apply=document.createElement('button'); apply.textContent='Aplicar'; apply.onclick=async()=>{state.query[entity.name]={search:search.value.trim(),sort:sort.value,order:order.value};state.page[entity.name]=1;setLoading(true);try{await loadEntity(entity);}catch(e){showError(e.message);}finally{setLoading(false);}};
    controlsTop.append(search,sort,order,apply); section.appendChild(controlsTop);
    const table=document.createElement('table'); const thead=document.createElement('thead'); const tr=document.createElement('tr');
    for (const f of entity.fields) { const th=document.createElement('th'); th.textContent=f; tr.appendChild(th); } const actionTh=document.createElement('th'); actionTh.textContent='Ações'; tr.appendChild(actionTh); thead.appendChild(tr); table.appendChild(thead);
    const tbody=document.createElement('tbody'); for (const row of pageRows(entity, rows)) { const r=document.createElement('tr'); for (const f of entity.fields) { const td=document.createElement('td'); td.textContent=row[f] ?? ''; r.appendChild(td); } const actions=document.createElement('td'); const edit=document.createElement('button'); edit.textContent='Editar'; edit.onclick=()=>editRow(entity,row); const del=document.createElement('button'); del.textContent='Excluir'; del.onclick=()=>removeRow(entity,row); actions.append(edit, ' ', del); r.appendChild(actions); tbody.appendChild(r); } table.appendChild(tbody); section.appendChild(table);
    const controls=document.createElement('div'); const page=state.page[entity.name]||1; const totalPages=Math.max(1,Math.ceil(rows.length/state.pageSize)); const prev=document.createElement('button'); prev.textContent='Anterior'; prev.disabled=page<=1; prev.onclick=()=>{state.page[entity.name]=page-1;renderData();}; const next=document.createElement('button'); next.textContent='Próxima'; next.disabled=page>=totalPages; next.onclick=()=>{state.page[entity.name]=page+1;renderData();}; const info=document.createElement('span'); info.textContent=` Página ${page} de ${totalPages} (${rows.length} registros) `; controls.append(prev,info,next); section.appendChild(controls); root.appendChild(section);
  }
}
async function refreshAll() { showError(''); setLoading(true); try { for (const entity of CONTRACT.entities) await loadEntity(entity); } catch(error) { showError(error.message); } finally { setLoading(false); } }
async function login(event) {
  event.preventDefault(); showError(''); setLoading(true);
  try {
    const email=$('#email').value; const password=$('#password').value;
    const result=await api('/api/auth/login', {method:'POST', body:JSON.stringify({email,password})});
    state.token=result.token || ''; if(state.token) localStorage.setItem('aurora_token', state.token);
    $('#auth').hidden=true; $('#app').hidden=false; renderForms(); await refreshAll(); showAuth('Login realizado', true);
  } catch(error) { showAuth('Falha no login'); showError(error.message); } finally { setLoading(false); }
}
$('#login-form').addEventListener('submit', login); $('#refresh').addEventListener('click', refreshAll);
if (state.token) { $('#auth').hidden=true; $('#app').hidden=false; renderForms(); refreshAll().catch(e=>showError(e.message)); }
""" % contract

    def _backend(self, spec):
        import json as _json
        fields = {e.name: e.fields for e in getattr(spec, 'entities', [])}
        template = """import json
import sqlite3
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "database" / "app.db"
SPEC = json.loads((ROOT / "aurora.app.json").read_text(encoding="utf-8"))
TOKENS = set()
ENTITY_FIELDS = __ENTITY_FIELDS__

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def _relationships():
    rel=[]
    names=set(ENTITY_FIELDS)
    for name, fields in ENTITY_FIELDS.items():
        for field in fields:
            if field.endswith('_id'):
                target=field[:-3]
                for candidate in names:
                    if candidate.lower()==target.lower() or candidate.lower()==target.lower().rstrip('s'):
                        rel.append({'from':name,'field':field,'to':candidate,'to_field':'id'})
    return rel

def init_db():
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS _aurora_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        for name, entity_fields in ENTITY_FIELDS.items():
            columns = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
            for field in entity_fields:
                if field == "id": continue
                kind = "REAL" if field in {"price", "amount", "total"} else "TEXT"
                columns.append(f'\"{field}\" {kind}')
            db.execute(f'CREATE TABLE IF NOT EXISTS \"{name}\" ({", ".join(columns)})')
        db.execute('INSERT OR IGNORE INTO _aurora_migrations(version) VALUES (1)')

def rows_for(name, query):
    fields=ENTITY_FIELDS[name]
    allowed=set(fields)
    search=(query.get('search') or [''])[0].strip()
    sort=(query.get('sort') or ['id'])[0]
    order=(query.get('order') or ['desc'])[0].lower()
    if sort not in allowed: sort='id'
    direction='ASC' if order=='asc' else 'DESC'
    sql=f'SELECT * FROM \"{name}\"'
    params=[]
    if search:
        searchable=[f for f in fields if f!='id']
        if searchable:
            sql += ' WHERE ' + ' OR '.join(f'CAST(\"{f}\" AS TEXT) LIKE ?' for f in searchable)
            params=[f'%{search}%']*len(searchable)
    sql += f' ORDER BY \"{sort}\" {direction}'
    try:
        page=max(1,int((query.get('page') or ['1'])[0])); limit=min(1000,max(1,int((query.get('limit') or ['100'])[0])))
    except ValueError: page,limit=1,100
    sql += ' LIMIT ? OFFSET ?'; params += [limit,(page-1)*limit]
    with connect() as db:
        cur=db.execute(sql,params); cols=[x[0] for x in cur.description]; items=[dict(zip(cols,row)) for row in cur.fetchall()]
        return {'items':items,'page':page,'limit':limit,'count':len(items),'search':search,'sort':sort,'order':order}

def create_row(name, payload):
    allowed = [f for f in ENTITY_FIELDS[name] if f != "id" and f in payload]
    if not allowed: raise ValueError("nenhum campo gravável informado")
    with connect() as db:
        cols = ", \".join(f'\"{f}\"' for f in allowed)
        marks = ", \".join("?" for _ in allowed)
        cur = db.execute(f'INSERT INTO \"{name}\" ({cols}) VALUES ({marks})', [payload[f] for f in allowed])
        ident = cur.lastrowid
    return {"id": ident, **{f: payload[f] for f in allowed}}

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type='application/json; charset=utf-8'):
        data = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(status); self.send_header('Content-Type', content_type); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
    def _json(self, status, payload): self._send(status, json.dumps(payload, ensure_ascii=False))
    def _body(self):
        length = int(self.headers.get('Content-Length', '0')); raw = self.rfile.read(length) if length else b'{}'; return json.loads(raw.decode('utf-8'))
    def authorized(self):
        if not SPEC.get('auth'): return True
        header = self.headers.get('Authorization','')
        return header.startswith('Bearer ') and header.split(' ',1)[1] in TOKENS
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/') or '/'
        query = parse_qs(parsed.query)
        if path == '/api/health': self._json(200, {'status':'ok'}); return
        if path == '/api/info': self._json(200, {'name': SPEC['name'], 'description': SPEC['description']}); return
        if path == '/api/meta/relationships': self._json(200, _relationships()); return
        if SPEC.get('auth') and path.startswith('/api/') and path not in ('/api/auth/login','/api/health') and not self.authorized(): self._json(401, {'error':'não autenticado'}); return
        for name in ENTITY_FIELDS:
            slug = name.lower() + 's'
            if path == f'/api/{slug}': self._json(200, rows_for(name, query)); return
            if path.startswith(f'/api/{slug}/'):
                try: ident = int(path.rsplit('/', 1)[-1])
                except ValueError: self._json(400, {'error':'id inválido'}); return
                with connect() as db:
                    cur = db.execute(f'SELECT * FROM \"{name}\" WHERE id = ?', (ident,)); row = cur.fetchone(); cols = [x[0] for x in cur.description]
                if row is None: self._json(404, {'error':'not found'}); return
                self._json(200, dict(zip(cols, row))); return
        if path in ('/', '/index.html'):
            file = ROOT / 'frontend' / 'index.html'
            if file.exists(): self._send(200, file.read_bytes(), 'text/html; charset=utf-8'); return
        self._json(404, {'error':'not found'})
    def do_POST(self):
        path = urlparse(self.path).path.rstrip('/') or '/'
        try: payload = self._body()
        except (ValueError, json.JSONDecodeError): self._json(400, {'error':'JSON inválido'}); return
        if path == '/api/auth/login':
            ok = bool(payload.get('email') and payload.get('password'))
            if not ok: self._json(401, {'authenticated': False, 'error':'credenciais obrigatórias'}); return
            token = secrets.token_urlsafe(24); TOKENS.add(token); self._json(200, {'authenticated': True, 'token': token}); return
        if SPEC.get('auth') and path.startswith('/api/') and not self.authorized(): self._json(401, {'error':'não autenticado'}); return
        for name in ENTITY_FIELDS:
            if path == f'/api/{name.lower()}s':
                try: self._json(201, create_row(name, payload))
                except (ValueError, sqlite3.Error) as exc: self._json(400, {'error': str(exc)})
                return
        self._json(404, {'error':'not found'})
    def do_PUT(self):
        path = urlparse(self.path).path.rstrip('/')
        if SPEC.get('auth') and path.startswith('/api/') and not self.authorized(): self._json(401, {'error':'não autenticado'}); return
        try: payload=self._body()
        except (ValueError, json.JSONDecodeError): self._json(400, {'error':'JSON inválido'}); return
        for name in ENTITY_FIELDS:
            prefix=f'/api/{name.lower()}s/'
            if path.startswith(prefix):
                try: ident=int(path[len(prefix):])
                except ValueError: self._json(400, {'error':'id inválido'}); return
                allowed=[f for f in ENTITY_FIELDS[name] if f!='id' and f in payload]
                if not allowed: self._json(400, {'error':'nenhum campo gravável informado'}); return
                with connect() as db:
                    exists=db.execute(f'SELECT 1 FROM "{name}" WHERE id=?',(ident,)).fetchone()
                    if not exists: self._json(404, {'error':'not found'}); return
                    sets=', '.join(f'"{f}"=?' for f in allowed)
                    db.execute(f'UPDATE "{name}" SET {sets} WHERE id=?',[payload[f] for f in allowed]+[ident])
                    cur=db.execute(f'SELECT * FROM "{name}" WHERE id=?',(ident,)); row=cur.fetchone(); cols=[x[0] for x in cur.description]
                self._json(200, dict(zip(cols,row))); return
        self._json(404, {'error':'not found'})
    def do_DELETE(self):
        path=urlparse(self.path).path.rstrip('/')
        if SPEC.get('auth') and path.startswith('/api/') and not self.authorized(): self._json(401, {'error':'não autenticado'}); return
        for name in ENTITY_FIELDS:
            prefix=f'/api/{name.lower()}s/'
            if path.startswith(prefix):
                try: ident=int(path[len(prefix):])
                except ValueError: self._json(400, {'error':'id inválido'}); return
                with connect() as db:
                    cur=db.execute(f'DELETE FROM "{name}" WHERE id=?',(ident,))
                    if cur.rowcount==0: self._json(404, {'error':'not found'}); return
                self._json(200, {'deleted':True,'id':ident}); return
        self._json(404, {'error':'not found'})

if __name__ == '__main__':
    init_db(); ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
"""
        return template.replace('__ENTITY_FIELDS__', _json.dumps(fields, ensure_ascii=False))

    def _relationships(self, spec):
        names = {e.name for e in getattr(spec, 'entities', [])}
        rel=[]
        for e in getattr(spec, 'entities', []):
            for field in e.fields:
                if not field.endswith('_id'): continue
                target=field[:-3]
                for candidate in names:
                    if candidate.lower()==target.lower() or candidate.lower()==target.lower().rstrip('s'):
                        rel.append({'from':e.name,'field':field,'to':candidate,'to_field':'id'})
        return rel

    def _schema(self, spec):
        entities = getattr(spec, 'entities', [])
        if not entities:
            return 'CREATE TABLE IF NOT EXISTS _aurora_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);\nCREATE TABLE IF NOT EXISTS app_metadata (id INTEGER PRIMARY KEY, key TEXT NOT NULL UNIQUE, value TEXT NOT NULL);\n'
        names={e.name for e in entities}; blocks=['CREATE TABLE IF NOT EXISTS _aurora_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);']
        for e in entities:
            cols=['id INTEGER PRIMARY KEY AUTOINCREMENT']
            for f in e.fields:
                if f != 'id':
                    col=f'"{f}" TEXT'
                    target=next((n for n in names if f.endswith('_id') and (n.lower()==f[:-3].lower() or n.lower()==f[:-3].lower().rstrip('s'))),None)
                    if target: col += f' REFERENCES "{target}"(id)'
                    cols.append(col)
            blocks.append(f'CREATE TABLE IF NOT EXISTS "{e.name}" ({", ".join(cols)});')
        return '\n'.join(blocks) + '\n'

    def _generated_tests(self, spec):
        return '''import json\nimport sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).parents[1]))\n\ndef test_generated_app_is_complete():\n    root = Path(__file__).parents[1]\n    spec = json.loads((root / 'aurora.app.json').read_text(encoding='utf-8'))\n    assert spec['name']\n    assert (root / 'backend' / 'main.py').exists()\n\ndef test_health_handler_contract():\n    from backend.main import Handler\n    assert hasattr(Handler, 'do_GET')\n'''

    def create_from_detailed_spec(self, detailed_spec):
        """Generate an app from DetailedAppSpec, treating its contract as authoritative."""
        spec = AppSpec(
            name=detailed_spec.name, kind=detailed_spec.kind, frontend=detailed_spec.frontend,
            backend=detailed_spec.backend, database=detailed_spec.database, auth=detailed_spec.auth,
            description=detailed_spec.description,
        )
        spec.entities = detailed_spec.entities
        spec.screens = detailed_spec.screens
        # Keep the visual contract attached to the generation spec so _files()
        # can materialize it for every generated application.
        spec.components = getattr(detailed_spec, 'components', [])
        spec.theme = getattr(detailed_spec, 'theme', {})
        files = self._files(spec)
        # Contract artifacts: routes, entity metadata, acceptance criteria and flows.
        files['frontend/components.json'] = json.dumps(self.component_runtime.normalize(spec.components), ensure_ascii=False, indent=2) + '\n'
        files['aurora.contract.json'] = json.dumps({
            'screens': [asdict(x) for x in detailed_spec.screens],
            'entities': [asdict(x) for x in detailed_spec.entities],
            'endpoints': [asdict(x) for x in detailed_spec.endpoints],
            'user_flows': list(detailed_spec.user_flows),
            'acceptance_criteria': [asdict(x) for x in detailed_spec.acceptance_criteria],
            'assumptions': list(detailed_spec.assumptions),
        }, ensure_ascii=False, indent=2) + '\n'
        files['backend/routes.json'] = json.dumps([asdict(x) for x in detailed_spec.endpoints], ensure_ascii=False, indent=2) + '\n'
        if detailed_spec.entities:
            files['database/entities.json'] = json.dumps([asdict(x) for x in detailed_spec.entities], ensure_ascii=False, indent=2) + '\n'
        files['docs/ACCEPTANCE.md'] = '# Critérios de aceitação\n\n' + ''.join(f'- [{x.id}] {x.text}\n' for x in detailed_spec.acceptance_criteria)
        files['docs/FLOWS.md'] = '# Fluxos de usuário\n\n' + ''.join(f'- {x}\n' for x in detailed_spec.user_flows)
        # Make the generated frontend reflect the declared screens/routes.
        if spec.kind in {'web','fullstack'}:
            nav = ''.join(f'<a href="{escape(x.route)}">{escape(x.name)}</a> ' for x in detailed_spec.screens)
            index = files.get('frontend/index.html','')
            index = index.replace('<main>', f'<nav>{nav}</nav><main>')
            files['frontend/index.html'] = index
        # Make the backend expose every declared GET/POST endpoint as a deterministic contract response.
        backend = files.get('backend/main.py','')
        marker = "        self._send(404, json.dumps({'error': 'not found'}))"
        routes = ""
        for ep in detailed_spec.endpoints:
            if ep.path in ('/api/health','/api/info'):
                continue
            path = ep.path.replace(':id', '')
            routes += f"        if self.path.rstrip('/') == '{path.rstrip('/')}' and '{ep.method}' == 'GET':\n            self._send(200, json.dumps({{'endpoint': '{ep.path}', 'method': 'GET', 'status': 'ok'}}))\n            return\n"
        if routes and marker in backend:
            backend = backend.replace(marker, routes + marker)
            files['backend/main.py'] = backend
        return self._write_generated(spec, files)

    def _write_generated(self, spec, files):
        slug = self._safe_name(spec.name)
        target = self.output_root / slug
        if target.exists() and any(target.iterdir()):
            raise FileExistsError(f'aplicativo já existe: {target}')
        target.mkdir(parents=True, exist_ok=True)
        created=[]
        for rel, content in files.items():
            path=target/rel; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8'); created.append(rel)
        return {'ok': True, 'path': str(target), 'spec': asdict(spec), 'files': created}

    def create(self, **kwargs):
        spec = AppSpec(**kwargs)
        if spec.kind not in {'web','fullstack','api','mobile'}:
            raise ValueError(f'tipo de aplicativo não suportado: {spec.kind}')
        slug = self._safe_name(spec.name)
        target = self.output_root / slug
        if target.exists() and any(target.iterdir()):
            raise FileExistsError(f'aplicativo já existe: {target}')
        return self._write_generated(spec, self._files(spec))

    def preview(self, **kwargs):
        spec = AppSpec(**kwargs)
        return {'spec': asdict(spec), 'files': sorted(self._files(spec))}
