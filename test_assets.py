import json
from aurora.assets import AssetManager

def test_icon_is_generated_and_indexed(tmp_path):
    result = AssetManager(tmp_path).icon('Logo Principal', 'Aurora', 256)
    assert result['ok']
    path = tmp_path / result['asset']['path']
    assert path.exists() and '<svg' in path.read_text(encoding='utf-8')
    manifest = json.loads((tmp_path / 'assets/manifest.json').read_text(encoding='utf-8'))
    assert manifest[0]['kind'] == 'icon'

def test_storyboard_is_generated(tmp_path):
    result = AssetManager(tmp_path).storyboard('promo', ['abertura', {'description':'produto', 'duration':4}])
    assert result['asset']['metadata']['scenes'] == 2
    data = json.loads((tmp_path / result['asset']['path']).read_text(encoding='utf-8'))
    assert data['scenes'][1]['duration'] == 4
