from __future__ import annotations
import json
from typing import Any

class QuestionGenerator:
    """Structured study-question generation through Aurora's model boundary."""
    def __init__(self, model): self.model = model
    def _fallback(self, topic, count, difficulty, kind):
        return {'ok': True, 'topic': topic, 'questions': [
            {'id': i+1, 'type': kind, 'difficulty': difficulty,
             'question': f'Questão {i+1} sobre {topic}.',
             'alternatives': ['A','B','C','D'] if kind == 'multiple_choice' else [],
             'answer': None, 'explanation': 'Configure um modelo de geração para conteúdo completo.'}
            for i in range(count)], 'generated_by': 'fallback'}
    def generate(self, topic: str, count=5, difficulty='medium', kind='multiple_choice', context='') -> dict[str, Any]:
        topic = str(topic or '').strip()
        if not topic: return {'ok': False, 'error': 'topic é obrigatório'}
        count = max(1, min(int(count or 5), 50))
        prompt = (f'Gere {count} questões de estudo sobre: {topic}\nNível: {difficulty}\n'
                  f'Tipo: {kind}\nContexto/material: {context}\n'
                  'Responda SOMENTE JSON: {"questions":[{"id":1,"type":"multiple_choice",'
                  '"difficulty":"medium","question":"...","alternatives":["A","B","C","D"],'
                  '"answer":"B","explanation":"..."}]}')
        try:
            data = json.loads(self.model.ask(prompt))
            questions = data.get('questions') if isinstance(data, dict) else None
            if not isinstance(questions, list): raise ValueError('JSON sem questions')
            return {'ok': True, 'topic': topic, 'questions': questions[:count], 'generated_by': 'model'}
        except Exception as exc:
            result = self._fallback(topic, count, difficulty, kind); result['warning'] = str(exc); return result
