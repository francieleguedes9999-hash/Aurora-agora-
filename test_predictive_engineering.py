from pathlib import Path
from aurora.predictive_engineering import PredictiveEngineering


class Impact:
    def analyze(self, target, depth=2, limit=50):
        return {'files': [target, 'aurora/other.py', 'tests/test_other.py'],
                'tests': ['tests/test_other.py'], 'fingerprint': 'impact'}


class Graph:
    pass


class Repairs:
    def similar(self, failure, diagnosis=None, target=None, limit=8):
        return [{'success': True, 'target': target, 'repair': 'reuse known fix'}]


def test_predictive_engineering_preflight(tmp_path):
    p = PredictiveEngineering(tmp_path, Impact(), Graph(), Repairs())
    result = p.predict('aurora/target.py')
    assert result['ok']
    assert result['predictions']
    assert result['high_risk_count'] >= 1
    assert result['preventive_tests'] == ['tests/test_other.py']
    assert p.status()['history'] == 1


def test_predictive_engineering_persists_and_preflights(tmp_path):
    p = PredictiveEngineering(tmp_path, Impact(), Graph(), Repairs())
    result = p.preflight('aurora/target.py')
    assert result['ok']
    assert result['risk'] == 'high'
    assert Path(tmp_path, '.aurora', 'predictive_engineering.json').exists()
