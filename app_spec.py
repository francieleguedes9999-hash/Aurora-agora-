from __future__ import annotations
import json, re, uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

@dataclass
class ComponentSpec:
    id: str
    type: str
    label: str = ''
    props: dict[str, Any] = field(default_factory=dict)

@dataclass
class ScreenSpec:
    id: str
    name: str
    purpose: str
    route: str
    components: list[str] = field(default_factory=list)
    layout: str = 'standard'

@dataclass
class EntitySpec:
    name: str
    fields: list[str] = field(default_factory=list)

@dataclass
class EndpointSpec:
    method: str
    path: str
    purpose: str

@dataclass
class AcceptanceCriterion:
    id: str
    text: str

@dataclass
class DetailedAppSpec:
    name: str
    description: str
    kind: str
    frontend: str
    backend: str
    database: str
    auth: bool
    screens: list[ScreenSpec]
    components: list[ComponentSpec]
    theme: dict[str, Any]
    entities: list[EntitySpec]
    endpoints: list[EndpointSpec]
    user_flows: list[str]
    acceptance_criteria: list[AcceptanceCriterion]
    assumptions: list[str] = field(default_factory=list)

class DetailedSpecBuilder:
    """Expands a short app description into a deterministic implementation contract."""
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.path = self.root / '.aurora' / 'app-spec.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def build(self, description: str, base: dict[str, Any] | None = None, persist: bool = True) -> DetailedAppSpec:
        text = (description or '').strip()
        if not text:
            raise ValueError('descrição do aplicativo vazia')
        base = dict(base or {})
        low = text.lower()
        name = base.get('name') or self._name(text)
        kind = base.get('kind') or ('api' if 'api' in low else 'mobile' if any(x in low for x in ('mobile','android','ios','celular')) else 'web')
        db = base.get('database') or ('sqlite' if any(x in low for x in ('banco','database','dados','cadastro')) else 'none')
        auth = bool(base.get('auth')) or any(x in low for x in ('login','autenticação','autenticacao','senha','conta'))
        screens = self._screens(text, auth)
        components = self._components(screens, text)
        theme = self._theme(text)
        entities = self._entities(text, db, auth)
        endpoints = self._endpoints(entities, auth)
        flows = self._flows(text, screens, auth)
        criteria = self._criteria(screens, endpoints, entities, auth)
        spec = DetailedAppSpec(name, text, kind, base.get('frontend','html'), base.get('backend','python'), db, auth,
                               screens, components, theme, entities, endpoints, flows, criteria,
                               ['Implementação local inicial; integrações externas serão adicionadas quando configuradas.'])
        if persist:
            self.path.write_text(json.dumps(asdict(spec), ensure_ascii=False, indent=2), encoding='utf-8')
        return spec

    def load(self) -> DetailedAppSpec | None:
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            return DetailedAppSpec(
                data['name'], data['description'], data['kind'], data['frontend'], data['backend'], data['database'], data['auth'],
                [ScreenSpec(**x) for x in data.get('screens',[])],
                [ComponentSpec(**x) for x in data.get('components',[])],
                data.get('theme', {}),
                [EntitySpec(**x) for x in data.get('entities',[])],
                [EndpointSpec(**x) for x in data.get('endpoints',[])],
                data.get('user_flows',[]), [AcceptanceCriterion(**x) for x in data.get('acceptance_criteria',[])], data.get('assumptions',[]))
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None


    def _components(self, screens, text):
        low=text.lower(); out=[]
        for screen in screens:
            if screen.id == 'login':
                out += [ComponentSpec('login-form','form','Entrar',{'fields':['email','password'],'submit':'Entrar'})]
            elif screen.id in {'catalog','tasks','dashboard','calendar'}:
                out += [ComponentSpec(f'{screen.id}-header','header',screen.name), ComponentSpec(f'{screen.id}-toolbar','toolbar','Ações'), ComponentSpec(f'{screen.id}-list','data-list',screen.name,{'pagination':True,'search':True})]
                if screen.id != 'calendar': out.append(ComponentSpec(f'{screen.id}-form','entity-form','Novo',{'mode':'create'}))
            else:
                out += [ComponentSpec(f'{screen.id}-header','header',screen.name), ComponentSpec(f'{screen.id}-content','content',screen.purpose)]
        return out

    def _theme(self, text):
        low=text.lower()
        return {'style':'responsive','density':'comfortable','radius':'12px','navigation':'topbar' if 'menu lateral' not in low else 'sidebar','features':['responsive','accessible','focus-states']}

    def _name(self, text):
        m = re.search(r'(?:app|aplicativo|sistema|site|plataforma|projeto)\s+(?:de|para|do|da)?\s*([\wÀ-ÿ -]{2,50})', text, re.I)
        if m:
            c = re.split(r'\s+(?:com|que|para|onde|usando|incluindo)\s+', re.sub(r'\s+',' ',m.group(1)).strip(' .,:;'), maxsplit=1, flags=re.I)[0]
            if c: return c.title()
        return 'Aurora App'

    def _screens(self, text, auth):
        low=text.lower(); out=[ScreenSpec('home','Início','Entrada principal do aplicativo','/', ['header','content','navigation'])]
        if auth: out += [ScreenSpec('login','Login','Autenticar usuário','/login',['form','email','password']), ScreenSpec('account','Conta','Gerenciar conta','/account',['profile','actions'])]
        if any(x in low for x in ('produto','loja','venda','catálogo','catalogo')): out += [ScreenSpec('catalog','Catálogo','Listar e consultar itens','/products',['search','list','filters']), ScreenSpec('product','Detalhes','Visualizar um item','/products/:id',['details','actions'])]
        elif any(x in low for x in ('tarefa','task','projeto')): out += [ScreenSpec('tasks','Tarefas','Listar e atualizar tarefas','/tasks',['list','form','filters'])]
        elif any(x in low for x in ('agenda','evento','calendário','calendario')): out += [ScreenSpec('calendar','Agenda','Visualizar e gerenciar eventos','/calendar',['calendar','form'])]
        else: out += [ScreenSpec('dashboard','Painel','Área principal de dados e ações','/dashboard',['summary','list','actions'])]
        return out

    def _entities(self,text,db,auth):
        if db=='none' and not auth: return []
        low=text.lower(); out=[]
        if auth: out.append(EntitySpec('User',['id','name','email','password_hash','created_at']))
        if any(x in low for x in ('produto','loja','catálogo','catalogo')): out.append(EntitySpec('Product',['id','name','description','price','stock','created_at']))
        elif any(x in low for x in ('tarefa','task')): out.append(EntitySpec('Task',['id','title','description','status','created_at']))
        elif any(x in low for x in ('evento','agenda','calendário','calendario')): out.append(EntitySpec('Event',['id','title','starts_at','ends_at','description']))
        if not out and db!='none': out.append(EntitySpec('Record',['id','name','created_at']))
        return out

    def _endpoints(self, entities, auth):
        out=[EndpointSpec('GET','/api/health','Verificar disponibilidade da API'), EndpointSpec('GET','/api/info','Consultar metadados do aplicativo')]
        if auth: out += [EndpointSpec('POST','/api/auth/login','Autenticar usuário'), EndpointSpec('GET','/api/me','Consultar usuário autenticado')]
        for e in entities:
            if e.name=='User': continue
            slug=e.name.lower()+'s'
            out += [EndpointSpec('GET',f'/api/{slug}',f'Listar {e.name}'), EndpointSpec('POST',f'/api/{slug}',f'Criar {e.name}'), EndpointSpec('GET',f'/api/{slug}/:id',f'Consultar {e.name}')]
        return out

    def _flows(self,text,screens,auth):
        flows=['Usuário abre o aplicativo e visualiza a tela inicial.']
        if auth: flows.append('Usuário informa credenciais, autentica e acessa a área protegida.')
        if len(screens)>2: flows.append('Usuário navega até a área principal, consulta dados e executa uma ação disponível.')
        flows.append('Aplicativo envia requisições à API e apresenta o resultado ou uma mensagem de erro compreensível.')
        return flows

    def _criteria(self,screens,endpoints,entities,auth):
        c=[AcceptanceCriterion(uuid.uuid4().hex[:8],'O projeto deve iniciar sem erro de importação ou sintaxe.'), AcceptanceCriterion(uuid.uuid4().hex[:8],'A interface deve carregar a tela inicial solicitada.')]
        for e in endpoints[:6]: c.append(AcceptanceCriterion(uuid.uuid4().hex[:8],f'O endpoint {e.method} {e.path} deve possuir contrato implementado ou explicitamente marcado como pendente.'))
        if auth: c.append(AcceptanceCriterion(uuid.uuid4().hex[:8],'Rotas e operações autenticadas devem exigir uma fronteira de autenticação.'))
        if entities: c.append(AcceptanceCriterion(uuid.uuid4().hex[:8],'As entidades previstas devem possuir representação persistente ou um motivo documentado para não persistirem.'))
        return c
