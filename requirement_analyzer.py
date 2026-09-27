from __future__ import annotations
import re
from typing import Any


class RequirementAnalyzer:
    """Turns a free-form app request into explicit, traceable requirements."""

    _feature_patterns = {
        'authentication': (r'\b(login|logar|autentica[cç][aã]o|senha|conta|usu[aá]rio)\b', 'Autenticação e contas de usuário'),
        'payments': (r'\b(pagamento|pagamentos|pix|cart[aã]o|checkout|cobran[cç]a)\b', 'Pagamentos/checkout'),
        'notifications': (r'\b(notifica[cç][aã]o|notificar|alerta|push|email|e-mail)\b', 'Notificações'),
        'search': (r'\b(busca|buscar|pesquisa|pesquisar|filtro|filtrar)\b', 'Busca e filtros'),
        'reports': (r'\b(relat[oó]rio|relat[oó]rios|dashboard|painel|gr[aá]fico|estat[ií]stica)\b', 'Relatórios/indicadores'),
        'files': (r'\b(arquivo|arquivos|upload|anexo|documento|foto|imagem)\b', 'Arquivos/mídia'),
        'real_time': (r'\b(tempo real|tempo-real|chat|mensagem|mensagens)\b', 'Interação em tempo real'),
        'api': (r'\b(api|endpoint|integra[cç][aã]o)\b', 'API/integrações'),
        'mobile': (r'\b(mobile|android|ios|celular|smartphone)\b', 'Experiência mobile'),
    }

    def analyze(self, request: str) -> dict[str, Any]:
        text = ' '.join((request or '').strip().split())
        low = text.lower()
        if not text:
            return {'ok': False, 'error': 'descrição vazia'}

        features = []
        for key, (pattern, label) in self._feature_patterns.items():
            if re.search(pattern, low, re.I):
                features.append({'id': key, 'label': label, 'source': 'explicit'})

        actions = self._actions(text)
        domain = self._domain(text)
        actors = self._actors(text)
        entities = self._entities(text)
        constraints = self._constraints(text)
        ambiguities = self._ambiguities(text, features, actors, entities)

        requirements = []
        for item in features:
            requirements.append({'id': f"req-{item['id']}", 'type': 'feature', 'text': item['label'], 'priority': 'high'})
        for action in actions:
            requirements.append({'id': f"req-action-{len(requirements)+1}", 'type': 'behavior', 'text': action, 'priority': 'high'})

        return {
            'ok': True,
            'request': text,
            'summary': f"Aplicativo para {domain}" if domain else 'Aplicativo definido a partir da solicitação do usuário',
            'domain': domain,
            'actors': actors,
            'features': features,
            'actions': actions,
            'entities': entities,
            'constraints': constraints,
            'ambiguities': ambiguities,
            'requirements': requirements,
            'completeness': self._completeness(features, actions, entities, constraints, ambiguities),
        }

    def _domain(self, text: str) -> str:
        low = text.lower()
        terms = ['loja', 'estudos', 'educação', 'agenda', 'finanças', 'vendas', 'estoque', 'tarefas', 'projetos', 'delivery', 'rede social', 'saúde']
        found = [t for t in terms if t in low]
        return found[0] if found else ''

    def _actors(self, text: str) -> list[str]:
        low = text.lower()
        out = []
        for word, label in [('aluno', 'Aluno'), ('professor', 'Professor'), ('cliente', 'Cliente'), ('admin', 'Administrador'), ('administrador', 'Administrador'), ('usuário', 'Usuário'), ('usuario', 'Usuário')]:
            if word in low and label not in out:
                out.append(label)
        return out or ['Usuário']

    def _entities(self, text: str) -> list[str]:
        low = text.lower()
        candidates = [('produto','Produto'), ('tarefa','Tarefa'), ('projeto','Projeto'), ('evento','Evento'), ('pedido','Pedido'), ('usuário','Usuário'), ('usuario','Usuário'), ('aluno','Aluno'), ('professor','Professor'), ('matéria','Matéria'), ('materia','Matéria'), ('questão','Questão'), ('questao','Questão'), ('prova','Prova')]
        return list(dict.fromkeys(label for word, label in candidates if word in low))

    def _actions(self, text: str) -> list[str]:
        low = text.lower()
        verbs = [('criar', 'Criar registros'), ('cadastrar', 'Cadastrar registros'), ('editar', 'Editar registros'), ('excluir', 'Excluir registros'), ('listar', 'Listar registros'), ('comprar', 'Realizar compras'), ('vender', 'Realizar vendas'), ('agendar', 'Agendar eventos'), ('acompanhar', 'Acompanhar status'), ('gerenciar', 'Gerenciar dados')]
        return list(dict.fromkeys(label for word, label in verbs if re.search(rf'\b{re.escape(word)}\w*\b', low)))

    def _constraints(self, text: str) -> list[str]:
        low = text.lower(); out=[]
        if 'mobile' in low or 'celular' in low: out.append('Interface responsiva para dispositivos móveis')
        if 'offline' in low or 'sem internet' in low: out.append('Funcionamento offline ou tolerância a indisponibilidade de rede')
        if 'tempo real' in low: out.append('Atualização em tempo real')
        if 'seguro' in low or 'segurança' in low: out.append('Requisitos de segurança devem ser considerados')
        return out

    def _ambiguities(self, text: str, features: list[dict], actors: list[str], entities: list[str]) -> list[str]:
        out=[]
        low=text.lower()
        if any(x in low for x in ('pagamento','pix','cartão','checkout')) and 'payments' in {x['id'] for x in features}:
            out.append('Provedor e credenciais de pagamento ainda não especificados')
        if any(x in low for x in ('notificação','email','push')):
            out.append('Canal/provedor de notificações ainda não especificado')
        if not entities:
            out.append('Entidades de negócio não foram explicitamente definidas')
        if len(actors) == 1 and any(x in low for x in ('admin','professor','cliente','aluno')):
            out.append('Permissões detalhadas por papel ainda não especificadas')
        return out

    def _completeness(self, features, actions, entities, constraints, ambiguities) -> dict[str, Any]:
        covered = sum(bool(x) for x in (features, actions, entities))
        score = round(min(1.0, covered / 3), 2)
        return {'score': score, 'level': 'high' if score >= .8 and not ambiguities else 'medium' if score >= .5 else 'low', 'missing': ambiguities}
