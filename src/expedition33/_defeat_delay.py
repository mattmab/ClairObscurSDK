"""Scoped override of the single audited battle defeat presentation wait."""
import secrets
import struct
from .invocation import InvocationError

SIZE = 20984


def encode(function, token, owner, mode):
    data = bytearray(SIZE)
    struct.pack_into('<4IQiiQQI', data, 0, 3, 227, 0, 0, owner,
                     function.index, function.serial, function.address, token, mode)
    result = bytes(data)
    validate_request(result)
    return result


def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE:
        raise ValueError('Defeat delay packet size')
    version, operation, error, state, owner, index, serial, address, token, mode = struct.unpack_from('<4IQiiQQI', data)
    if ((version, operation, error, state) != (3, 227, 0, 0) or not owner or
            index < 0 or serial <= 0 or not 0x10000 <= address <= 0x7fffffffffff or
            address & 7 or not token or mode not in (1, 2) or any(data[52:])):
        raise ValueError('Invalid fixed defeat delay override request')


class DefeatDelayOverride:
    def __init__(self, scope, function):
        scope._check()
        if getattr(scope._session._transport, 'defeat_delay_override_protocol', 0) != 1:
            raise RuntimeError('Instant defeat retry requires native runtime 255 or newer')
        from ._stable_lease import acquire_stable
        self._scope = scope
        self._owner = secrets.randbits(64) or 1
        self._held = acquire_stable(scope, function)[0]
        self._function, self._token = self._held.object, self._held._token
        self._active = True  # Register before any potentially uncertain command.
        scope._register_native_owner(self)
        self._command(1)

    def _command(self, mode):
        scope = self._scope
        packet = encode(self._function, self._token, self._owner, mode)
        session = scope._session
        session._check()  # Cleanup remains available after callback scope revocation.
        transport = session._transport
        previous = getattr(transport, '_lease_owner', 0)
        transport._lease_owner = scope._lease_owner_id
        try:
            raw = transport.command('mesh', packet)
        finally:
            transport._lease_owner = previous
        reply = bytes.fromhex(raw['mesh_packet'])
        if len(reply) != SIZE or reply[:8] != packet[:8] or reply[16:] != packet[16:]:
            raise RuntimeError('Uncorrelated defeat delay acknowledgement; owner retained')
        error, state = struct.unpack_from('<2I', reply, 8)
        if error:
            if mode == 1 and error == 3790 and state == 0:
                self._active = False
            raise InvocationError('Defeat delay override rejected; owner retained' if self._active else
                                  'Defeat delay signature differs from the audited build',
                                  outcome='unknown' if state == 2 else 'not_dispatched', native_error=error)
        if state != (1 if mode == 1 else 0):
            raise RuntimeError('Unknown defeat delay override state; owner retained')

    def close(self):
        if self._active:
            self._command(2)
            self._active = False
        if not self._scope._closed and self._held.active:
            self._held.release()
        return True
