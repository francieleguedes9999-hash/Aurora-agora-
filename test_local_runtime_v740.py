from aurora.local_access import LocalAccess
from aurora.local_runtime import LocalRuntimePolicy


def test_local_runtime_defaults_to_loopback(tmp_path):
    access = LocalAccess(tmp_path)
    policy = LocalRuntimePolicy(access)
    assert policy.validate_bind('127.0.0.1')['remote'] is False
    assert policy.validate_bind('localhost')['remote'] is False
    assert policy.status()['login_required'] is False


def test_remote_binding_requires_explicit_opt_in(tmp_path):
    policy = LocalRuntimePolicy(LocalAccess(tmp_path))
    try:
        policy.validate_bind('0.0.0.0')
    except PermissionError:
        pass
    else:
        raise AssertionError('remote binding should require explicit opt-in')
    assert policy.validate_bind('0.0.0.0', allow_remote=True)['remote'] is True
