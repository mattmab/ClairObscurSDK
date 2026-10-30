"""Owned, finite playback endpoint evidence; this is not an OnFinished hook.

The adapter must supply native-validated frame-time returns and the exact same
current owner context on every observation. Idle alone never establishes an end.
The exact exclusive-upper cursor clamp was demonstrated in a live retained
player before cleanup or any Stop call. It uses no wall-clock timing.
"""
from fractions import Fraction

from ._pod_values import NumericStructValue, QUALIFIED_FRAME_TIME, encode

# Exact shipping FFrameTime exclusive-upper clamp observed before any Stop:
# integer EndTime N -> current N-1 + the greatest binary32 value below one.
# This is a fixed representation contract, not a timing tolerance.
MAX_SUBFRAME = float.fromhex('0x1.fffffep-1')


def _context(value):
    if type(value) is not tuple or len(value) != 3:
        raise ValueError('Immutable world/controller/player identities required')
    for identity in value:
        if (type(identity) is not tuple or len(identity) != 4 or
                any(type(number) is not int for number in identity) or
                identity[0] <= 0 or identity[1] < 0 or identity[2] <= 0 or
                identity[3] < 0x10000 or identity[3] % 8):
            raise ValueError('Complete positive current object identities required')
    if len({identity[0] for identity in value}) != 1:
        raise ValueError('Sequence context belongs to multiple processes')
    return value


def qualified_time(value):
    """Return an exact rational time from the supported copied return codec."""
    if type(value) is not NumericStructValue or value.path != QUALIFIED_FRAME_TIME:
        raise ValueError('Native copied QualifiedFrameTime required')
    numerator, denominator = value['Rate']['Numerator'], value['Rate']['Denominator']
    if numerator <= 0 or denominator <= 0:
        raise ValueError('Positive frame rate required')
    subframe = value['Time']['SubFrame']
    if not 0 <= subframe < 1:
        raise ValueError('Canonical frame subframe required')
    frame = Fraction(value['Time']['FrameNumber']['Value']) + Fraction(subframe)
    return frame * denominator / numerator


class OwnedSequenceEndpoint:
    """One playback attempt's conservative finite-endpoint journal.

    Context includes exact world/controller/player identities, not just a map
    path. A public mutation is marked pending BEFORE dispatch. A lost response,
    unrecognised mutation or context replacement permanently invalidates this
    attempt. An explicit Stop, including one at the final frame, is cancellation.
    """
    def __init__(self, context, end_time):
        self.context = _context(context)
        self.end_time = qualified_time(end_time)
        if end_time['Time']['SubFrame'] != 0. or end_time['Time']['FrameNumber']['Value'] <= -(1 << 31):
            raise ValueError('Supported endpoint requires an integer exclusive upper frame')
        self._end_bytes = encode(QUALIFIED_FRAME_TIME, end_time)
        self._terminal_bytes = encode(QUALIFIED_FRAME_TIME, {
            'Time': {'FrameNumber': {'Value': end_time['Time']['FrameNumber']['Value']-1},
                     'SubFrame': MAX_SUBFRAME},
            'Rate': dict(end_time['Rate']),
        })
        self.state = 'ready'
        self.seen_playing = False
        self._pending = None
        self._serial = 0

    def begin_command(self, name):
        if self._pending is not None or self.state in ('unknown', 'cancelled', 'endpoint_observed'):
            raise RuntimeError('Sequence endpoint attempt is terminal or pending')
        if name not in ('Play', 'Pause', 'SetPlayRate', 'Stop'):
            self.state = 'unknown'
            raise RuntimeError('Unreviewed sequence mutation invalidates endpoint evidence')
        if name == 'Play' and self.state not in ('ready', 'paused'):
            self.state = 'unknown'
            raise RuntimeError('Only first Play or acknowledged resume is admitted')
        if name == 'Pause' and self.state != 'playing':
            raise RuntimeError('Only a playing attempt may pause')
        self._serial += 1
        self._pending = (self._serial, name, self.state)
        self.state = 'unknown'
        return self._serial

    def finish_command(self, ticket, *, returned):
        if self._pending is None or ticket != self._pending[0]:
            self._pending = None
            self.state = 'unknown'
            raise RuntimeError('Sequence command acknowledgement differs')
        _, name, previous = self._pending
        self._pending = None
        if returned is not True:
            self.state = 'unknown'
        elif name == 'Stop':
            self.state = 'cancelled'
        elif name == 'Play':
            self.state = 'playing'
        elif name == 'Pause':
            self.state = 'paused'
        else:
            self.state = previous

    def observe(self, *, context, current_time, end_time, playing, paused):
        if type(playing) is not bool or type(paused) is not bool:
            self.state = 'unknown'
            raise ValueError('Exact playing and paused observations required')
        if self._pending is not None or self.state == 'unknown':
            return self.state
        try:
            context = _context(context)
        except ValueError:
            self.state = 'unknown'
            raise
        if context != self.context:
            self.state = 'unknown'
            return self.state
        try:
            current, end = qualified_time(current_time), qualified_time(end_time)
        except (ValueError, TypeError, KeyError):
            self.state = 'unknown'
            raise
        if (encode(QUALIFIED_FRAME_TIME, end_time) != self._end_bytes or
                current > end or (playing and paused)):
            self.state = 'unknown'
        elif self.state in ('cancelled', 'endpoint_observed', 'ready'):
            pass
        elif playing:
            self.seen_playing = True
        elif not paused and self.state == 'playing':
            self.state = ('endpoint_observed' if self.seen_playing and
                          encode(QUALIFIED_FRAME_TIME, current_time) == self._terminal_bytes
                          else 'interrupted')
        return self.state


def current_owned_context(sequence):
    """Prove this exact owned pair is in the current visible PersistentLevel.

    This role-specific check does not enumerate/truncate World.Levels or admit
    arbitrary streamed actors. The native owner remains authoritative for every
    player invocation and retirement; this function supplies copied attribution.
    """
    from ._reader import shared_operation, active_reader
    from .catalog import capture_selected
    from .cinematics.original_game_action import controller_context
    from .cinematics.history import field, identity
    from .values import read_values_with_references, capture_selected_values

    scope = sequence.scope
    scope._check()
    with shared_operation(scope.pid, _executable=scope._session._transport._executable):
        capability=getattr(scope._session._transport,'stable_lease_protocol',0)
        if type(capability) is int and capability==1:
            from .cinematics.controller_anchor import for_scope
            # The playback scope already prepared this selector for its input
            # snapshot. Reuse that parent's retained LocalPlayer identity;
            # every context projection below remains fresh and bracketed.
            parent_reference=getattr(scope,'_parent',None)
            parent=parent_reference() if parent_reference is not None else None
            anchor_scope=parent if parent is not None else scope
            anchor_scope._check()
            if anchor_scope._session is not scope._session:
                raise RuntimeError('Sequence controller anchor belongs to another session')
            observe_context=for_scope(anchor_scope).context
        else:
            observe_context=lambda:controller_context(scope._session,project=True)
        context = observe_context()
        required = (tuple(context['controller'][1:]), tuple(context['world'][1:]),
                    (sequence.actor.index, sequence.actor.serial, sequence.actor.address),
                    (sequence.player.index, sequence.player.serial, sequence.player.address))
        reader=active_reader()
        projected=(reader is not None and getattr(reader,'supports_catalog_values',False) is True)
        level_hint=None
        if projected:
            previous=getattr(sequence,'catalog',None)
            candidate=previous.by_index.get(sequence.actor.outer_index) if previous is not None else None
            if (candidate is not None and candidate.class_name=='Level' and candidate.pid==scope.pid and
                    candidate.serial>0 and candidate.serial==sequence.actor.outer_serial):
                level_hint=candidate
        if projected:
            # One fresh bounded projection replaces repeated target/descriptor
            # reads. Context still brackets both projections, and the native
            # owner validates every subsequent player invocation independently.
            targets=required+((identity(level_hint)[1:],) if level_hint is not None else ())
            fields=('PersistentLevel','SequencePlayer','LevelSequenceAsset','Sequence')
            if level_hint is not None:fields+=('OwningWorld','bIsVisible')
            catalog, copied = capture_selected_values(scope.pid,targets,fields=fields,references=True)
        else:
            catalog = capture_selected(scope.pid, required)
        controller, world, actor, player = (catalog.by_index[item[0]] for item in required)
        for expected, observed in zip(required, (controller, world, actor, player)):
            if (identity(observed)[1:] != expected or observed.object_flags & 0x40018030 or
                    getattr(observed, 'item_flags', 0) & 0x200000):
                raise RuntimeError('Owned sequence context identity changed or is retiring')
        if (catalog.path_name(catalog.by_index[actor.class_index]) != '/Script/LevelSequence.LevelSequenceActor' or
                catalog.path_name(catalog.by_index[player.class_index]) != '/Script/LevelSequence.LevelSequencePlayer'):
            raise RuntimeError('Owned sequence pair class changed')
        if projected:values=copied[world.index]
        else:values, catalog = read_values_with_references(catalog, world, fields=('PersistentLevel',))
        level = field(values, 'PersistentLevel', 'ObjectProperty')
        if level is None or level.class_name != 'Level':
            raise RuntimeError('Current PersistentLevel is unavailable')
        if (actor.outer_index, actor.outer_serial) != (level.index, level.serial):
            raise RuntimeError('Owned sequence actor is outside the current PersistentLevel')
        if (player.outer_index, player.outer_serial) != (actor.index, actor.serial):
            raise RuntimeError('Owned sequence player is outside its factory actor')
        if projected:
            if level_hint is not None:
                # The hint supplies a selector only. Its exact identity and
                # values were freshly read alongside the world/player pair.
                if identity(level)!=identity(level_hint):raise RuntimeError('Owned sequence PersistentLevel changed')
                values=copied[level.index]
            else:
                _, level_values=capture_selected_values(scope.pid,
                    ((level.index,level.serial,level.address),),fields=('OwningWorld','bIsVisible'),references=True)
                values=level_values[level.index]
        else:values, catalog = read_values_with_references(catalog, level, fields=('OwningWorld', 'bIsVisible'))
        owning = field(values, 'OwningWorld', 'ObjectProperty')
        if (owning is None or identity(owning) != tuple(context['world']) or
                field(values, 'bIsVisible', 'BoolProperty') is not True):
            raise RuntimeError('Owned sequence level is not current and visible')
        if projected:values=copied[actor.index]
        else:values, catalog = read_values_with_references(catalog, actor, fields=('SequencePlayer', 'LevelSequenceAsset'))
        reciprocal = field(values, 'SequencePlayer', 'ObjectProperty')
        if reciprocal is None or identity(reciprocal) != identity(player):
            raise RuntimeError('Owned sequence factory pair is not reciprocal')
        actor_asset = field(values, 'LevelSequenceAsset', 'ObjectProperty')
        if projected:values=copied[player.index]
        else:values, catalog = read_values_with_references(catalog, player, fields=('Sequence',))
        player_asset = field(values, 'Sequence', 'ObjectProperty')
        if (actor_asset is None or player_asset is None or
                identity(actor_asset) != identity(sequence._asset) or
                identity(player_asset) != identity(sequence._asset)):
            raise RuntimeError('Owned sequence pair no longer references its retained source asset')
        if observe_context() != context:
            raise RuntimeError('Owned sequence context changed during observation')
        return _context((tuple(context['world']), tuple(context['controller']), identity(player)))
