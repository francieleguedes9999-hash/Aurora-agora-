from pathlib import Path
from aurora.media_engine import MediaEngine

def test_local_media_engine(tmp_path):
    m = MediaEngine(tmp_path)
    image = m.generate('image', 'mapa de estudo')
    assert image['ok'] and Path(image['path']).exists()
    audio = m.generate('audio', 'narração')
    assert audio['ok'] and Path(audio['path']).exists()
    status = m.status()
    assert status['local_provider']['available'] is True

def test_video_provider_is_explicit(tmp_path):
    m = MediaEngine(tmp_path)
    result = m.generate('video', 'aula de matemática', duration=1)
    assert result['provider'] == 'local_artifact'
    assert 'ok' in result
