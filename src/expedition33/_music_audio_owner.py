"""Build-specific cleanup for a detached Expedition 33 music-system instance.

Only its verified map/array audio references are owned; fire-and-forget sounds
and arbitrary cinematic callbacks remain outside this contract.
"""
import secrets
import struct
from dataclasses import replace
from . import _invocation_wire as call

HEADER = struct.Struct('<IIQQII')
SIZE = 32 + 64 + 2*call.SIZE

def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE: raise ValueError('Music owner size')
    version, op, owner, reserved, error, state = HEADER.unpack_from(data)
    if version != 1 or op not in (1,2,3,4,5) or not owner or reserved or error or state:
        raise ValueError('Music owner header')
    if op in (2,3,5) and any(data[32:]): raise ValueError('Unexpected music owner payload')
    if op == 4 and (any(data[32:96]) or any(data[96+call.SIZE:])):
        raise ValueError('Unexpected audio pause payload')

class NativeMusicAudioOwner:
    def __init__(self, scope):
        self.scope = scope
        self.owner = secrets.randbits(64) or 1
        self.state = 'new'
        self._sounds = []
        self._retiring = False
        scope._audio_owners.append(self)

    def create_sound(self, planner, panel, sound, *, volume=1.0, pitch=1.0):
        """Create silent, natively owned 2D audio in this isolated playback scope.

        The returned component can use normal reflected Play/SetPaused calls.
        Its retained result stays with this scope until native Stop/Destroy has
        completed. This does not intercept a cinematic's PlaySound2D events.
        """
        import math
        self.scope._check()
        session = self.scope._session
        if getattr(session._transport, 'owned_sound_protocol', 0) != 1:
            raise RuntimeError('Runtime does not support owned sound creation')
        if self.state != 'armed' or planner._scope is None or planner._scope() is not self.scope:
            raise RuntimeError('An armed audio owner and its scoped planner are required')
        if panel.state != 'open' or panel.uncertain or panel.scope._session is not session:
            raise RuntimeError('An open panel in this session is required')
        capacity=getattr(session._transport,'owned_sound_capacity',16)
        maximum=getattr(session._transport,'owned_sound_volume_max',1)
        if type(capacity) is not int or capacity not in (16,32) or type(maximum) is not int or maximum not in (1,2):
            raise RuntimeError('Invalid owned sound capacity/volume capability')
        if len(self._sounds)>=capacity:
            raise RuntimeError('Owned sound capacity reached before factory dispatch')
        if type(volume) not in (int,float) or type(pitch) not in (int,float) or not math.isfinite(volume) or not 0 <= volume <= maximum or not math.isfinite(pitch) or not .25 <= pitch <= 2:
            raise ValueError(f'Volume must be 0..{maximum} and pitch .25..2')
        catalog = planner._catalog
        def one(rows):
            rows = tuple(rows)
            if len(rows) != 1: raise ValueError('Ambiguous audio factory identity')
            return rows[0]
        cls = one(o for o in catalog.objects if o.name == 'GameplayStatics' and o.class_name == 'Class')
        default = one(o for o in catalog.objects if o.class_index == cls.index and o.name == 'Default__GameplayStatics')
        fn = one(o for o in catalog.objects if o.outer_index == cls.index and o.name == 'CreateSound2D' and o.class_name == 'Function')
        prepared = planner.prepare(default, fn, WorldContextObject=panel.player, Sound=sound,
            VolumeMultiplier=float(volume), PitchMultiplier=float(pitch), StartTime=0.0,
            ConcurrencySettings=None, bPersistAcrossLevelTransition=False, bAutoDestroy=False)
        # This factory has only the original scalar/object parameter types.
        # A POD-capable planner defaults to v2 even for scalar-only calls.
        prepared._plan = replace(prepared._plan, wire_version=1)
        result = prepared.invoke(refresh_from_result=True)
        self._sounds.append(result)
        component = result.return_value
        if component is None: raise RuntimeError('Audio device rejected component creation')
        if component.class_name != 'AudioComponent':
            session._abort_ownership()
            raise RuntimeError('Owned audio factory returned an unexpected component')
        return component

    def pause_original_audio(self, plan):
        self.scope._check()
        if self.state != 'armed' or getattr(self.scope._session._transport, 'original_audio_pause_protocol', 0) != 1:
            raise RuntimeError('Original audio pause ownership unavailable')
        payload = bytes(64) + call.encode_plan(replace(plan, wire_version=1)) + bytes(call.SIZE)
        return self._send(4, payload)

    def _send(self, op, payload=None):
        session = self.scope._session
        session._check()
        if self.state == 'unknown': raise RuntimeError('Unknown music cleanup ownership')
        request = HEADER.pack(1,op,self.owner,0,0,0) + (payload or bytes(SIZE-32))
        validate_request(request)
        self.state = 'unknown'
        try:
            reply = session._transport.command('music-audio-owner', request)
            data = bytes.fromhex(reply['music_audio_packet'])
            if len(data) != SIZE or data[:24] != request[:24] or data[32:] != request[32:]:
                raise ValueError('Music owner acknowledgement mismatch')
            error, state = HEADER.unpack_from(data)[4:]
            if error == 407 and (state in (1,3) or (op==5 and state==0)):
                self.state = 'armed' if state else 'closed'; return False
            if error or state not in (0,1): raise RuntimeError(f'Music owner rejected ({error}, {state})')
            self.state = 'armed' if state else 'closed'
            return True
        except BaseException:
            if op==5:
                self.state='unknown'
                raise
            session._abort_ownership()
            raise

    def prepare(self, original, isolated, audio_class, stop, destroy):
        self.scope._check()
        if self.state != 'new': raise RuntimeError('Music owner already used')
        refs = (original,isolated,audio_class)
        if any(o.pid != self.scope.pid for o in refs): raise ValueError('Music identity session mismatch')
        leases = [self.scope.retain(o) for o in refs[:2]]
        payload = b''.join(struct.pack('<iiQ',o.index,o.serial,o.address) for o in refs)
        payload += struct.pack('<QQ',*(lease._token for lease in leases))
        payload += b''.join(call.encode_plan(replace(p,wire_version=1)) for p in (stop,destroy))
        return self._send(1,payload)

    def status(self):
        self._send(3); return self.state

    def close(self):
        if self.state in ('new','closed'): return True
        if self._retiring:return self.retire_world()
        return self._send(2)

    def retire_world(self):
        if self.state=='new':return True
        value=getattr(self.scope._session._transport,'music_audio_retirement_protocol',0)
        if type(value) is not int or value!=1:
            raise RuntimeError('Verified native retired-world audio cleanup required')
        self._retiring=True
        return self._send(5)
