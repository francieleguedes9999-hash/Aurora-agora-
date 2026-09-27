"""Local-first runtime policy for Aurora.

The personal installation is usable without an account. By default the web UI
binds only to loopback so another machine cannot reach it accidentally.
Remote binding requires an explicit opt-in and is never implied by login state.
"""
import ipaddress

class LocalRuntimePolicy:
    def __init__(self, access):
        self.access = access

    @staticmethod
    def is_loopback(host):
        if host in ('localhost',):
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def validate_bind(self, host, allow_remote=False):
        if self.is_loopback(host):
            return {'allowed': True, 'host': host, 'remote': False}
        if not allow_remote:
            raise PermissionError('Aurora local mode accepts only loopback binding unless remote access is explicitly enabled.')
        return {'allowed': True, 'host': host, 'remote': True, 'warning': 'remote access explicitly enabled'}

    def status(self):
        return {
            'mode': 'local_owner',
            'login_required': False,
            'remote_identity_required': False,
            'default_bind': '127.0.0.1',
            'remote_bind_requires_explicit_opt_in': True,
        }
