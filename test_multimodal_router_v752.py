from aurora.multimodal_router import MultimodalRouter

class M:
    def available(self): return False
    def ask(self, request, inputs=None): return 'ok'

class Q:
    def generate(self, topic, count, difficulty, typ, context):
        return {'ok': True, 'topic': topic, 'count': count}

class Media:
    def status(self): return {'ok': True, 'providers': ['local_artifact']}
    def generate(self, kind, prompt, provider, **kwargs):
        return {'ok': True, 'kind': kind, 'provider': provider, 'ai_generated': False}

class A:
    model=M(); question_generator=Q(); media=Media()

def test_routes_questions_locally():
    r=MultimodalRouter(A())
    assert r.classify('faça 10 questões de matemática')['kind']=='questions'
    assert r.run('faça questões', count=10)['count']==10

def test_local_media_does_not_require_key():
    r=MultimodalRouter(A())
    out=r.run('crie um vídeo sobre o sistema solar')
    assert out['provider']=='local_artifact'
    assert out['ai_generated'] is False
    assert r.status()['third_party_key_required'] is False
