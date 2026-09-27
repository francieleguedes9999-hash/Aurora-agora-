import json
from pathlib import Path
from aurora.training_lab import TrainingLab


def test_multimodal_materials_and_context(tmp_path):
    lab = TrainingLab(str(tmp_path / 'lab'))
    lab.add('topic', 'Python', 'Python é uma linguagem para automação.', tags=['programacao'])
    lab.add('voice', 'Aula de Python', '', transcript='Funções agrupam comportamentos reutilizáveis.', tags=['python'])
    lab.add('video', 'Curso', '', transcript='Vamos construir uma API.', tags=['api'])
    lab.add('article', 'Matéria sobre APIs', 'APIs conectam sistemas.', source='https://example.com/a', tags=['api'])
    assert lab.status()['items'] == 4
    assert lab.status()['by_kind']['voice'] == 1
    assert 'APIs conectam' in lab.context('API sistemas', limit=4)


def test_file_and_dataset_export(tmp_path):
    lab = TrainingLab(str(tmp_path / 'lab'))
    src = tmp_path / 'material.txt'
    src.write_text('Conteúdo de treinamento sobre agentes.', encoding='utf-8')
    item = lab.add_file(str(src), kind='document', tags=['agentes'])
    assert item['content'].startswith('Conteúdo de treinamento')
    out = Path(lab.export_dataset('meu_dataset'))
    assert out.exists()
    row = json.loads(out.read_text(encoding='utf-8').splitlines()[0])
    assert row['tags'] == ['agentes']
    assert 'agentes' in row['text']
