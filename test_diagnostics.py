from aurora.diagnostics import diagnose

def test_syntax_diagnostic_extracts_location():
    r = {'ok': False, 'stderr': '  File "src/app.py", line 7\n    x = (\nSyntaxError: unexpected EOF while parsing', 'stdout': ''}
    d = diagnose(r)
    assert d['kind'] == 'syntax'
    assert d['file'] == 'src/app.py'
    assert d['line'] == 7
    assert d['ok'] is False

def test_import_diagnostic():
    d = diagnose({'ok': False, 'stderr': 'ModuleNotFoundError: No module named x', 'stdout': ''})
    assert d['kind'] == 'import'
    assert d['hints']

def test_success_diagnostic():
    d = diagnose({'ok': True, 'stdout': 'ok', 'stderr': ''})
    assert d['ok'] is True
    assert d['kind'] == 'success'
