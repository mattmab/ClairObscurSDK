"""Continent human flight using Harness-discovered engine functions.

Requires the SDK Vector argument extension. No game files/save edits.
"""
import ctypes
import logging
import math
import time
from contextlib import nullcontext
from expedition33.catalog import capture_matching
from expedition33._reader import ReadBatch
from expedition33.management import Action, Keybind, ModDefinition
from expedition33.values import read_values
from expedition33.invocation import InvocationError

LOG = logging.getLogger('expedition33.continent_flight')
HORIZONTAL_SPEED = 1200.0
VERTICAL_SPEED = 1200.0
RESPONSE_SECONDS = 0.35
MAX_ACCELERATION = 2400.0


class ExplorationNotReady(RuntimeError):
    """Read-only discovery found no supported pawn; no call was prepared."""


def flight_velocity(movement, vertical):
    x, y = movement['X'], movement['Y']
    magnitude = math.hypot(x, y)
    scale = HORIZONTAL_SPEED / max(1.0, magnitude)
    return {'X': x * scale, 'Y': y * scale, 'Z': vertical * VERTICAL_SPEED}


def smooth_correction(desired, current, elapsed):
    dt = max(0.0, min(elapsed, .1))
    alpha = 1.0 - math.exp(-dt / RESPONSE_SECONDS)
    delta = {axis: (desired[axis] - current[axis]) * alpha for axis in 'XYZ'}
    length = math.sqrt(sum(value * value for value in delta.values()))
    limit = MAX_ACCELERATION * dt
    if length > limit and length:
        delta = {axis: value * limit / length for axis, value in delta.items()}
    return delta


class DoubleTap:
    def __init__(self, window=.4):
        self.window, self.last = window, None

    def press(self, now):
        previous, self.last = self.last, now
        if previous is not None and 0 <= now - previous <= self.window:
            self.last = None
            return True
        return False


class Mod:
    def __init__(self):
        self.session = self.planner = None
        self.flying = False
        self.tap = DoubleTap()
        self.error = None
        self.direction = 0
        self.calls = {}
        self.last_poll = time.monotonic()
        self.input_state = {}
        self.cached_observations = None
        self.enable_ms = None
        self.next_discovery = 0.
        self.next_identity_check = 0.
        self.restore_mode = None

    def management(self):
        return ModDefinition('continent-flight', 'Continent Flight', version='0.4-experimental',
            description='F6 toggles flight on the current exploration character. Space remains jump. E/Q ascend/descend. Travel resets flight.',
            actions=(Action('status', 'Flight status', self.status),
                     Action('refresh', 'Find current exploration character', self.refresh),
                     Action('land', 'Leave flight', self.land)),
            keybinds=(Keybind('fly', 'Toggle flight (keep separate from jump)', 'F6', self.toggle),
                      Keybind('rise', 'Hold to ascend', 'E', self.rise),
                      Keybind('descend', 'Hold to descend', 'Q', self.descend)))

    def enable(self, session):
        if not getattr(session, 'supports_vector_values', False):
            raise RuntimeError('Continent Flight requires Vector support. Use the native Mods launcher (unified pause-menu runtime).')
        self.session = session
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.user32.GetForegroundWindow.restype = ctypes.c_void_p
        self.user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        started = time.perf_counter()
        try:
            self._prepare(use_cache=True)
        except ExplorationNotReady as error:
            # Enabled preference survives mounted startup. Existing discovery
            # polling attaches after dismount; flight itself remains off.
            self.error = str(error)
            self.next_discovery = time.monotonic() + 2.
        session.console.expose('continent_flight', self)
        session.actions.register('continent_flight.status', self.status, mutates=False)
        session.actions.register('continent_flight.toggle', self.toggle)
        session.actions.register('continent_flight.land', self.land)
        self.enable_ms = (time.perf_counter() - started) * 1000
        LOG.info('Ready in %.1f ms: F6 toggles flight; Space remains jump', self.enable_ms)

    def refresh(self, _):
        if self.flying:
            self.land(None)
        self.cached_observations = None
        self._prepare(use_cache=False)
        return self.local_status()

    def _prepare(self, *, use_cache):
        cached = self.cached_observations if use_cache else None
        try:
            with nullcontext() if cached else ReadBatch(self.session.pid):
                self._prepare_calls(cached)
        except Exception:
            # The next explicit enable rediscovers; never reuse rejected data or
            # retry an invocation whose dispatch outcome could be uncertain.
            self.cached_observations = None
            raise

    def _prepare_calls(self, cached):
        names = ('CharMoveComp', 'SetMovementMode', 'K2_GetActorLocation', 'IsFlying',
                 'GetLastInputVector', 'GetVelocity', 'AddImpulse', 'StopMovementImmediately',
                 'IsLocallyControlled', 'Vector', 'EMovementMode')
        catalog = cached.catalog if cached else capture_matching(self.session.pid,
            names=names, classes=('BP_jRPG_Character_WorldMap_pawn_C', 'BP_jRPG_Character_World_C', 'PlayerController'))
        controller_class = catalog.find_class('Controller').index
        player_class = catalog.find_class('PlayerController').index
        candidates = []
        for controller in catalog.select('PlayerController'):
            if controller.object_flags & 0x10: continue
            values = read_values(catalog, controller).values
            if values.get((player_class, 'bIsLocalPlayerController')) is not True: continue
            current = values.get((controller_class, 'Pawn'))
            if current is not None and current.class_name in (
                    'BP_jRPG_Character_WorldMap_pawn_C', 'BP_jRPG_Character_World_C'):
                candidates.append(current)
        if len(candidates) != 1:
            raise ExplorationNotReady('Waiting for one locally possessed exploration character')
        pawn = candidates[0]
        moves = [o for o in catalog.objects if o.outer_index == pawn.index and o.name == 'CharMoveComp']
        if len(moves) != 1:
            raise RuntimeError('Expected the exploration character movement component')
        movement = moves[0]
        self.movement = movement
        self.movement_class = catalog.find_class('CharacterMovementComponent').index
        functions = {catalog.path_name(o): o for o in catalog.objects if o.class_name == 'Function'}
        if self.planner:
            self.planner.close()
        self.planner = self.session.invocation_planner(**({'observations': cached} if cached else {'catalog': catalog}))
        def prepare(path, target=pawn, **args):
            return self.planner.prepare(target, functions[path], **args)
        self.calls = {
            'enter': prepare('/Script/Engine.CharacterMovementComponent:SetMovementMode', target=movement, NewMovementMode=5, NewCustomMode=0),
            'exit': prepare('/Script/Engine.CharacterMovementComponent:SetMovementMode', target=movement, NewMovementMode=0, NewCustomMode=0),
            'location': prepare('/Script/Engine.Actor:K2_GetActorLocation'),
            'is_flying': prepare('/Script/Engine.NavMovementComponent:IsFlying', target=movement),
            'input': prepare('/Script/Engine.PawnMovementComponent:GetLastInputVector', target=movement),
            'velocity': prepare('/Script/Engine.Actor:GetVelocity'),
            'impulse': prepare('/Script/Engine.CharacterMovementComponent:AddImpulse', target=movement, Impulse={'X':0.0,'Y':0.0,'Z':0.0}, bVelocityChange=True),
            'stop': prepare('/Script/Engine.MovementComponent:StopMovementImmediately', target=movement),
            'controlled': prepare('/Script/Engine.Pawn:IsLocallyControlled'),
        }
        self.pawn = catalog.path_name(pawn)
        self.error = None
        self.restore_mode = None
        self.tap = DoubleTap()
        # Read-only native calls validate cached target/function identities before readiness.
        # A rejection is surfaced, never retried as a mutation.
        if not self.invoke('controlled'):
            raise RuntimeError('Exploration character possession changed during discovery')
        self.invoke('is_flying')
        self.cached_observations = self.planner.observations()

    def invoke(self, name):
        try:
            with self.calls[name].invoke() as result:
                return result.return_value
        except InvocationError as error:
            if error.native_error == 202 and error.outcome == 'not_dispatched':
                self._forget_target('Exploration character changed; waiting to rediscover')
            raise

    def _forget_target(self, reason):
        # Revocation is local only: never call the destroyed pawn to clean up.
        self.flying = False
        self.direction = 0
        self.restore_mode = None
        self.cached_observations = None
        self.calls = {}
        if self.planner: self.planner.close()
        self.planner = None
        self.error = reason
        self.next_discovery = time.monotonic() + 1.

    def toggle(self, _=None):
        if self.error and self.calls:
            raise RuntimeError('Flight stopped after an error; explicit refresh required: ' + self.error)
        if not self.calls:
            raise RuntimeError(self.error or 'Waiting for exploration character')
        if not self.invoke('controlled'):
            self.direction = 0
            raise RuntimeError('The exploration character is not currently controlled')
        if self.flying:
            return self.land(None)
        values = read_values(self.planner._catalog, self.movement).values
        mode = values.get((self.movement_class, 'MovementMode'))
        custom = values.get((self.movement_class, 'CustomMovementMode'))
        if type(mode) is not int or type(custom) is not int or mode in (0, 5):
            raise RuntimeError('Cannot capture a supported pre-flight movement mode')
        self.restore_mode = (mode, custom)
        self.calls['exit'] = self.calls['exit'].bind(NewMovementMode=mode, NewCustomMode=custom)
        self.invoke('enter')
        self.flying = True
        self.last_poll = time.monotonic()
        LOG.info('Flight enabled for %s', self.pawn)
        return self.status(None)

    def space(self, _):
        if self.tap.press(time.monotonic()):
            self.toggle(None)

    def rise(self, _):
        if self.flying:
            self.direction = 1

    def descend(self, _):
        if self.flying:
            self.direction = -1

    def poll(self):
        now = time.monotonic()
        elapsed, self.last_poll = now - self.last_poll, now
        if not self.calls:
            if self.session is not None and now >= self.next_discovery:
                self.next_discovery = now + 2.
                try:
                    self._prepare(use_cache=False)
                    LOG.info('Attached to current exploration character: %s; flight remains off', self.pawn)
                except Exception as exc:
                    if self.planner: self.planner.close()
                    self.planner = None
                    self.calls = {}
                    self.error = str(exc)
            return
        if self.error:
            return
        if not self.flying:
            if now >= self.next_identity_check:
                self.next_identity_check = now + .5
                try:
                    if not self.invoke('controlled'):
                        self._forget_target('Possession changed; waiting to rediscover')
                except Exception as exc:
                    self.error = str(exc)
            return
        pid = ctypes.c_ulong()
        self.user32.GetWindowThreadProcessId(self.user32.GetForegroundWindow(), ctypes.byref(pid))
        self.input_state = dict(foreground_pid=pid.value, target_pid=self.session.pid,
                               direction=self.direction, elapsed=elapsed)
        if pid.value != self.session.pid:
            self.direction = 0
            return
        if self.direction:
            key = 69 if self.direction > 0 else 81
            if not self.user32.GetAsyncKeyState(key) & 0x8000:
                self.direction = 0
        try:
            if not self.invoke('controlled'):
                self.land()
                self._forget_target('Possession changed; waiting to rediscover')
                return
            if not self.invoke('is_flying'):
                self.input_state['controlled_flight'] = False
                self.direction = 0
                return
            self.input_state['controlled_flight'] = True
            desired = flight_velocity(self.invoke('input'), self.direction)
            current = self.invoke('velocity')
            correction = smooth_correction(desired, current, elapsed)
            if any(abs(value) > 1.0 for value in correction.values()):
                with self.calls['impulse'].bind(Impulse=correction, bVelocityChange=True).invoke():
                    pass
        except Exception as exc:
            self.direction = 0
            if isinstance(exc, InvocationError) and exc.native_error == 202 and exc.outcome == 'not_dispatched':
                self._forget_target('Exploration character changed; waiting to rediscover')
            self.error = str(exc)
            LOG.exception('Flight input stopped; no automatic mutation retry')

    def land(self, _=None):
        self.direction = 0
        if self.flying:
            try:
                self.invoke('stop')
                self.invoke('exit')
            except InvocationError as error:
                if error.native_error != 202 or error.outcome != 'not_dispatched': raise
            self.flying = False
            LOG.info('Flight disabled')
        return self.local_status()

    def local_status(self):
        state = dict(flying=self.flying, pawn=getattr(self, 'pawn', None), error=self.error,
                     horizontal_speed=HORIZONTAL_SPEED, vertical_speed=VERTICAL_SPEED,
                     input_state=self.input_state, enable_ms=self.enable_ms)
        return state

    def status(self, _=None):
        state = self.local_status()
        if self.calls:
            state['engine_flying'] = self.invoke('is_flying')
            state['location'] = dict(self.invoke('location'))
            state['velocity'] = dict(self.invoke('velocity'))
        return state

    def disable(self):
        try:
            self.land(None)
        finally:
            if self.planner:
                self.planner.close()
            self.calls = {}
            self.planner = self.session = None
