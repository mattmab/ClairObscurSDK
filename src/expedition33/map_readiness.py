"""Copied map collision evidence and bounded, identity-bound reveal decisions.

Scene visibility is observed separately from GPU completion. The caller must
supply its presentation/streaming readiness observation before revealing; this
module never substitutes elapsed time for that evidence.
"""
from dataclasses import dataclass
import math
import struct

SIZE = 20984
OPERATION = 107


class ReadinessPending(RuntimeError):
    """An exact native read could not prove readiness; keep the bounded guard."""


def prepare_readiness_metadata(session):
    """Prepare only Script functions/CDO during process loading, once per SDK."""
    cached = getattr(session, '_map_readiness_metadata', None)
    if cached is not None:
        return cached
    from ._reader import ReadBatch
    from .catalog import capture_matching
    from ._metadata_stabilization import process_preparation
    with ReadBatch(session.pid):
        catalog = capture_matching(session.pid, names=(
            'Default__KismetSystemLibrary', 'LineTraceSingle',
            'BreakHitResult', 'GetCollisionEnabled', 'WasRecentlyRendered',
            'IsStreamingStatePending'))
        paths = ('/Script/Engine.Default__KismetSystemLibrary',
                 '/Script/Engine.KismetSystemLibrary:LineTraceSingle',
                 '/Script/Engine.GameplayStatics:BreakHitResult',
                 '/Script/Engine.PrimitiveComponent:GetCollisionEnabled',
                 '/Script/Engine.PrimitiveComponent:WasRecentlyRendered',
                 '/Script/Engine.LevelStreaming:IsStreamingStatePending')
        discovered = tuple(catalog.find_path(path) for path in paths)
        stable = process_preparation(session).prepare(catalog, discovered)
        cached = tuple(stable.by_index[obj.index] for obj in discovered)
    session._map_readiness_metadata = cached
    return cached


def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE:
        raise ValueError('Map readiness packet size')
    version, operation, error, state, owner = struct.unpack_from('<4IQ', data)
    if (version != 3 or operation != OPERATION or error or state or not owner
            or any(data[24:88])):
        raise ValueError('Map readiness header')
    for at in range(88, 248, 16):
        index, serial, address = struct.unpack_from('<iiQ', data, at)
        if index < 0 or serial < 0 or not address:
            raise ValueError('Map readiness identity')
    if (any(data[248:2000]) or struct.unpack_from('<I', data, 2000)[0] > 1
            or struct.unpack_from('<I', data, 2004)[0] >= 2**31 or any(data[2008:])):
        raise ValueError('Map readiness padding or support policy')


@dataclass(frozen=True)
class Receipt:
    rows: int
    live_rows: int
    collision_query_rows: int
    visible_rows: int
    support_samples: int
    support_hits: int
    owned_support_hits: int
    flags: int
    rendered_rows: int
    streaming_levels: int
    streaming_pending: int
    rendered_support_hits: int
    owned_rendered_support_hits: int
    support_heights: tuple

    @property
    def spawn_complete(self):
        return bool(self.flags & 2)

    @property
    def collision_ready(self):
        return bool(self.flags & 4)

    @property
    def scene_visible(self):
        return bool(self.flags & 8)

    @property
    def visual_ready(self):
        # Owned visible floors need recent render evidence. Vanilla support may
        # be an invisible collision proxy; engine streaming covers that case.
        # This is observed scene readiness, not a GPU-idle assertion.
        return bool(self.flags & 16)


class NativeMapReadiness:
    """One read-only query on the already-owned map; never retries mutations."""
    def __init__(self, runtime, expected, *, expected_token=None, require_owned_support=False):
        if type(require_owned_support) is not bool:
            raise ValueError('Owned support policy must be bool')
        self.runtime = runtime
        self.expected = dict(expected)
        self.require_owned_support = require_owned_support
        self.ids = None
        self.expected_token = None
        if expected_token is not None:
            self.expected_token = self._token(expected_token)

    def _token(self, token):
        if (not isinstance(token, (tuple, list)) or len(token) != 4
                or type(token[3]) is not int or not 0 <= token[3] < 2**31):
            raise ValueError('Map readiness saved-world token')
        identities = []
        for identity in token[:3]:
            if not isinstance(identity, (tuple, list)) or len(identity) not in (3, 4):
                raise ValueError('Map readiness save identity')
            if len(identity) == 4:
                if identity[0] != self.runtime.scope.pid:
                    raise ValueError('Map readiness save identity process mismatch')
                identity = identity[1:]
            if (any(type(v) is not int for v in identity)
                    or identity[0] < 0 or identity[1] < 0 or identity[2] <= 0):
                raise ValueError('Map readiness save identity')
            identities.append(tuple(identity))
        if identities[0] != tuple(self.expected['visit']):
            raise ValueError('Map readiness save world mismatch')
        return (*identities, token[3])

    def prepare(self):
        if self.ids is None:
            self.ids = prepare_readiness_metadata(self.runtime.scope._session)
        return self

    def query(self):
        if self.expected_token is None:
            raise RuntimeError('Map readiness requires the current saved-world token')
        self.prepare()
        runtime = self.runtime
        if not runtime.started or runtime.uncertain or runtime._closed:
            raise RuntimeError('Owned map readiness unavailable')
        packet = bytearray(SIZE)
        struct.pack_into('<4IQ', packet, 0, 3, OPERATION, 0, 0, runtime.owner)
        identities = self.ids + (self.expected['visit'], self.expected['pawn']) + self.expected_token[1:3]
        for i, obj in enumerate(identities):
            value = ((obj.index, obj.serial, obj.address)
                     if not isinstance(obj, (tuple, list)) else tuple(obj))
            struct.pack_into('<iiQ', packet, 88 + 16*i, *value)
        struct.pack_into('<I', packet, 2000, int(self.require_owned_support))
        struct.pack_into('<I', packet, 2004, self.expected_token[3])
        validate_request(bytes(packet))
        with runtime.scope._lease_context():
            reply = runtime.scope._session._transport.command('mesh', bytes(packet))
        raw = bytes.fromhex(reply['mesh_packet'])
        if len(raw) != SIZE:
            raise RuntimeError('Map readiness acknowledgement size')
        compare = bytearray(raw)
        for start, end in ((8, 16), (3564, 3568), (4096, 4192)):
            compare[start:end] = packet[start:end]
        if compare != packet:
            raise RuntimeError('Map readiness acknowledgement mismatch')
        error, state = struct.unpack_from('<II', raw, 8)
        if error == 2115 and state in (0, 1):
            raise ReadinessPending('Map readiness observation pending (2115)')
        if error or state != 1:
            raise RuntimeError(f'Map readiness query rejected ({error}, {state})')
        counts = struct.unpack_from('<13I', raw, 4096)
        heights = struct.unpack_from('<5d', raw, 4152)
        rows, live, collision, visible, samples, hits, owned, flags, rendered, levels, pending, rendered_hits, owned_rendered = counts
        native_rows = struct.unpack_from('<I', raw, 3564)[0]
        if (rows > 6000 or rows != native_rows or rows != len(runtime.objects)
                or live > rows or collision > live or visible > live
                or samples != 5 or hits > samples or owned > hits or flags > 31
                or rendered > live or levels > 4096 or pending > levels
                or rendered_hits > hits or owned_rendered > min(owned, rendered_hits)
                or any(raw[4148:4152])
                or not flags & 1 or bool(flags & 2) != (rows == live)
                or bool(flags & 4) != (hits == 5 and
                    (not self.require_owned_support or owned == 5))
                or bool(flags & 8) != (rows == visible)
                or bool(flags & 16) != (rows == visible and pending == 0 and owned_rendered == owned)
                or any(not math.isfinite(z) or abs(z) > 1.e8 for z in heights)):
            raise RuntimeError('Map readiness report malformed')
        return Receipt(*counts, heights)


class RevealDecision:
    """A load generation's deadline and readiness contract, without a timer wait.

Cleanup is invoked exactly once on failure/cancel; it must release only resources
owned by this generation. A token change is a cancellation, never new admission.
"""
    def __init__(self, token, *, started, timeout, cleanup):
        if (token is None or not math.isfinite(started) or not math.isfinite(timeout)
                or not 0 < timeout <= 120 or not callable(cleanup)):
            raise ValueError('Map reveal generation/deadline')
        self.token = token
        self.deadline = started + timeout
        self.cleanup = cleanup
        self.state = 'loading'
        self.reason = None
        self._cleaned = False

    def cancel(self, reason='cancelled'):
        if self.state == 'ready':
            return self.state
        self.state = 'failed'
        self.reason = reason
        if not self._cleaned:
            self._cleaned = True
            self.cleanup(reason)
        return self.state

    def observe(self, receipt, *, token, now, visual_ready=False, restoration_ready=False):
        if self.state in ('ready', 'failed'):
            return self.state
        if not math.isfinite(now):
            return self.cancel('invalid_clock')
        if token is not None and token != self.token:
            return self.cancel('load_generation_changed')
        if now >= self.deadline:
            return self.cancel('readiness_timeout')
        if token is None or receipt is None:
            self.state = 'observation_pending'
        elif not receipt.spawn_complete:
            self.state = 'spawning'
        elif not receipt.collision_ready:
            self.state = 'collision_pending'
        elif not receipt.visual_ready or visual_ready is not True:
            self.state = 'visual_pending'
        elif restoration_ready is not True:
            self.state = 'player_pending'
        else:
            self.state = 'ready'
        return self.state
