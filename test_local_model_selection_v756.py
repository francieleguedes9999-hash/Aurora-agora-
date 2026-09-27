from aurora.local_model import LocalModelManager


def test_selects_coder_for_programming_task():
    mgr = LocalModelManager()
    models = [{'name': 'llama3:latest'}, {'name': 'qwen3-coder:latest'}]
    result = mgr.select_for_task('crie um aplicativo em Python', models=models)
    assert result['ok'] is True
    assert result['selected'] == 'qwen3-coder:latest'


def test_selects_vision_model_for_image_task():
    mgr = LocalModelManager()
    models = [{'name': 'llama3:latest'}, {'name': 'llava:latest'}]
    result = mgr.select_for_task('analise esta imagem', models=models)
    assert result['selected'] == 'llava:latest'


def test_never_downloads_and_defaults_to_installed_model():
    mgr = LocalModelManager()
    result = mgr.select_for_task('converse comigo', models=[{'name': 'llama3:latest'}])
    assert result['selected'] == 'llama3:latest'
