from __future__ import annotations
from typing import Any

class MultimodalRouter:
    """Routes requests to local-first Aurora capabilities.

    No third-party API key is required when the selected capability is local.
    Remote providers are optional and are only used when explicitly configured.
    """
    def __init__(self, agent):
        self.agent = agent

    def classify(self, request: str) -> dict[str, Any]:
        text = str(request or '').strip().lower()
        if any(w in text for w in ('vídeo', 'video', 'filme', 'animação')):
            kind = 'video'
        elif any(w in text for w in ('imagem', 'foto', 'ilustração', 'desenho')):
            kind = 'image'
        elif any(w in text for w in ('áudio', 'audio', 'som', 'narração', 'narracao', 'voz')):
            kind = 'audio'
        elif any(w in text for w in ('questão', 'questoes', 'questões', 'simulado', 'pergunta')):
            kind = 'questions'
        else:
            kind = 'text'
        return {'ok': True, 'kind': kind, 'local_first': True}

    def run(self, request: str, **options) -> dict[str, Any]:
        route = self.classify(request)
        kind = route['kind']
        if kind == 'questions':
            return self.agent.question_generator.generate(
                options.get('topic') or request,
                options.get('count', 5),
                options.get('difficulty', 'medium'),
                options.get('type', 'multiple_choice'),
                options.get('context', ''),
            )
        if kind in {'image', 'audio', 'video'}:
            return self.agent.media.generate(
                kind, request, options.get('provider', 'local_artifact'),
                **options.get('media_options', {}),
            )
        try:
            return {'ok': True, 'kind': 'text', 'response': self.agent.model.ask(request, inputs=options.get('inputs'))}
        except TypeError:
            return {'ok': True, 'kind': 'text', 'response': self.agent.model.ask(request)}

    def status(self) -> dict[str, Any]:
        return {
            'ok': True,
            'local_first': True,
            'text_model_available': bool(self.agent.model.available()),
            'media': self.agent.media.status(),
            'third_party_key_required': False,
            'third_party_key_required_when_remote_provider_selected': True,
        }
