from aurora.component_runtime import ComponentRuntime

def test_entity_form_gets_behavior():
    out=ComponentRuntime().normalize([{'id':'f','type':'entity-form','props':{}}])[0]
    assert out['props']['behavior']['api'] is True
    assert out['props']['behavior']['validation'] is True

def test_data_list_gets_search_refresh():
    out=ComponentRuntime().normalize([{'id':'l','type':'data-list','props':{}}])[0]
    assert out['props']['behavior']['search'] is True
    assert out['props']['behavior']['refresh'] is True

def test_validate_duplicate_ids():
    out=ComponentRuntime().validate([{'id':'x','type':'button'},{'id':'x','type':'form'}])
    assert not out['ok'] and 'x' in out['errors'][0]['ids']
