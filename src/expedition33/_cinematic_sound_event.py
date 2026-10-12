"""Exact-build Prologue sound-event adapter; not arbitrary Blueprint invocation."""
import secrets
import struct
from dataclasses import replace
from . import _invocation_wire as call

HEADER = struct.Struct('<IIQQIIII')
SIZE = 40 + 56 + call.SIZE

def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE: raise ValueError('Cinematic event packet size')
    version, op, owner, reserved, error, state, observed, failed = HEADER.unpack_from(data)
    if version not in (1,2) or op not in (1,2,3,4) or not owner or reserved or error or state or observed or failed:
        raise ValueError('Cinematic event header')
    if version == 2 and op == 1 and (any(data[72:88]) or any(data[96:])):
        raise ValueError('Empty event trap cannot contain sound or invocation')
    if op != 1 and any(data[40:]): raise ValueError('Unexpected cinematic event payload')

class NativeCinematicSoundEvent:
    def __init__(self, scope):
        self.scope = scope
        self.owner = secrets.randbits(64) or 1
        self.state = 'new'
        self.version = 1
        self.observed = self.failed = 0
        scope._audio_owners.append(self)

    def _send(self, op, payload=None):
        session = self.scope._session
        session._check()
        if self.state == 'unknown': raise RuntimeError('Cinematic event ownership is unknown')
        request = HEADER.pack(self.version,op,self.owner,0,0,0,0,0)+(payload or bytes(SIZE-40))
        validate_request(request)
        self.state = 'unknown'
        try:
            reply = session._transport.command('cinematic-sound-event',request)
            data = bytes.fromhex(reply['cinematic_sound_event_packet'])
            if len(data)!=SIZE or data[:24]!=request[:24] or data[40:]!=request[40:]:
                raise ValueError('Cinematic event acknowledgement mismatch')
            error,state,self.observed,self.failed = HEADER.unpack_from(data)[4:]
            if error==407 and state==1:
                self.state='armed'; return False
            if self.version == 2 and not error and state in (0,1,2):
                if self.failed > self.observed or (state == 1 and self.failed) or (state == 2 and not self.failed):
                    raise ValueError('Invalid empty-event trap state')
                self.state = {0:'closed',1:'armed',2:'quarantined'}[state]
                return True
            if error or state not in (0,1) or self.failed:
                raise RuntimeError(f'Cinematic event rejected ({error}, {state}, failed={self.failed})')
            self.state='armed' if state else 'closed'
            return True
        except BaseException:
            session._abort_ownership()
            raise

    def prepare(self, function, player, sound, play):
        self.scope._check()
        if self.state!='new': raise RuntimeError('Cinematic event owner already used')
        if getattr(self.scope._session._transport,'cinematic_sound_event_protocol',0)!=1:
            raise RuntimeError('Runtime has no verified cinematic event adapter')
        if any(o.pid!=self.scope.pid for o in (function,player,sound)):
            raise ValueError('Cinematic event identity session mismatch')
        lease=self.scope.retain(function)
        payload=b''.join(struct.pack('<iiQ',o.index,o.serial,o.address) for o in (function,player,sound))
        payload+=struct.pack('<Q',lease._token)
        payload+=call.encode_plan(replace(play,wire_version=1))
        return self._send(1,payload)

    def prepare_empty(self, function, player):
        """Arm only the exact native-admitted unexpected-event suppression trap.

        This never executes a sound or arbitrary function. A selected event is
        a controlled failure requiring the parent replay to stop and clean up.
        """
        self.scope._check()
        if self.state != 'new': raise RuntimeError('Cinematic event owner already used')
        transport = self.scope._session._transport
        if type(getattr(transport,'cinematic_empty_title_protocol',0)) is not int or transport.cinematic_empty_title_protocol != 1:
            raise RuntimeError('Runtime has no verified empty-title trap')
        if any(o.pid != self.scope.pid for o in (function,player)):
            raise ValueError('Empty event identity session mismatch')
        lease=self.scope.retain(function)
        payload=b''.join(struct.pack('<iiQ',o.index,o.serial,o.address) for o in (function,player))
        payload+=bytes(16)+struct.pack('<Q',lease._token)+bytes(call.SIZE)
        self.version=2
        return self._send(1,payload)

    def status(self):
        self._send(3)
        return dict(state=self.state,observed=self.observed,failed=self.failed)

    def diagnostics(self):
        """Observe bounded route stages; counters alone do not prove audible output."""
        session = self.scope._session
        session._check()
        if getattr(session._transport, 'cinematic_sound_diagnostics_protocol', 0) != 1:
            raise RuntimeError('Sound route diagnostics unavailable')
        if self.state not in ('armed', 'quarantined'):
            raise RuntimeError('Sound route diagnostics require an active owner')
        request = HEADER.pack(self.version,4,self.owner,0,0,0,0,0) + bytes(SIZE-40)
        try:
            reply = session._transport.command('cinematic-sound-event', request)
            data = bytes.fromhex(reply['cinematic_sound_event_packet'])
            if len(data) != SIZE or data[:24] != request[:24] or any(data[64:]):
                raise ValueError('Sound diagnostic acknowledgement mismatch')
            error, state, observed, failed = HEADER.unpack_from(data)[4:]
            counts = struct.unpack_from('<6I', data, 40)
            if (error or state not in (1,2) or any(a < b for a,b in zip(counts[:4], counts[1:5]))
                    or failed > counts[5] or counts[5] > counts[0]
                    or (self.version == 1 and counts[4] < 0xffffffff and observed != counts[4])
                    or (self.version == 2 and observed > counts[4])):
                raise ValueError('Invalid sound diagnostic counters')
            self.observed, self.failed = observed, failed
            self.state = 'armed' if state == 1 else 'quarantined'
            return dict(zip(('eligible_game_thread_calls', 'exact_function_frames', 'exact_directors',
                             'player_matches', 'selected_dispatches', 'failures'), counts))
        except BaseException:
            self.state = 'unknown'
            session._abort_ownership()
            raise

    def close(self):
        if self.state in ('new','closed'): return True
        return self._send(2)
