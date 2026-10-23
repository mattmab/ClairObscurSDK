"""Continent human flight using Harness-discovered engine functions.

Requires the SDK Vector argument extension. No game files/save edits.
"""
import ctypes
import logging
import math
import time
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from expedition33.catalog import capture_matching
from expedition33._reader import ReadBatch, active_reader
from expedition33.management import Action, Keybind, ModDefinition
from expedition33.values import read_values
from expedition33.invocation import InvocationError
from expedition33.keys import VIRTUAL_KEYS

LOG = logging.getLogger('expedition33.continent_flight')
HORIZONTAL_SPEED = 6000.0
VERTICAL_SPEED = 6000.0
RESPONSE_SECONDS = 0.35
MAX_ACCELERATION = 12000.0
FLIGHT_TUNING = {'MaxFlySpeed': HORIZONTAL_SPEED,
                 'MaxAcceleration': 6000.0, 'BrakingDecelerationFlying': 12000.0}
VERTICAL_TUNING = {'MaxAcceleration': 18000.0, 'BrakingDecelerationFlying': 0.0}


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


def discover_snapshot(pid, cached=None):
    """Pure reflection reads; never accesses a scope or prepares engine calls."""
    names = ('CharMoveComp', 'SetMovementMode', 'K2_GetActorLocation', 'IsFlying',
             'GetLastInputVector', 'GetVelocity', 'AddImpulse', 'StopMovementImmediately',
             'IsLocallyControlled', 'AddInputVector', 'Vector', 'EMovementMode')
    catalog = cached if cached is not None else capture_matching(pid,
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
    return catalog, pawn, movement


def discover_worker(pid):
    # Construct and close the reader on this one worker thread.
    with ReadBatch(pid):
        return discover_snapshot(pid)


class Mod:
    def __init__(self):
        self.session = self.planner = None
        self.flying = False
        self.tap = DoubleTap()
        self.error = None
        self.direction = 0
        self.direction_key = None
        self.calls = {}
        self.last_poll = time.monotonic()
        self.input_state = {}
        self.cached_observations = None
        self.enable_ms = None
        self.next_discovery = 0.
        self.next_identity_check = 0.
        self.restore_mode = None
        self.reader = None
        self.next_slow_diagnostic = 0.
        self.discovery_worker = None
        self.discovery_future = None
        self.discovery_generation = 0
        self.discovery_pending_generation = None
        self.disabled = False
        self.flight_tuning = []
        self.next_flight_check = 0.
        self.vertical_profile = False

    def _diagnose_slow(self, phase, started, error=None):
        elapsed = (time.perf_counter() - started) * 1000
        now = time.monotonic()
        if elapsed >= 100 and now >= self.next_slow_diagnostic:
            self.next_slow_diagnostic = now + 5.
            LOG.info('Flight slow phase=%s elapsed_ms=%.2f prepared_calls=%s flying=%s error=%s reader_closed=%s',
                phase, elapsed, len(self.calls), self.flying, error,
                getattr(self.reader, '_closed', None))

    def _close_reader(self):
        reader, self.reader = self.reader, None
        if reader is not None:
            reader.close()

    @contextmanager
    def operation(self):
        # Bind only during this mod's work. Every query still validates live
        # identities; retaining the worker does not retain query results.
        if active_reader() is not None:
            with ReadBatch(self.session.pid):
                yield
            return
        if self.reader is None:
            self.reader = ReadBatch(self.session.pid, share=True)
        owner = self.reader
        try:
            with owner.bind():
                yield
        except ExplorationNotReady:
            # A valid discovery can find no supported pawn (mounted/menu
            # startup). Keep its healthy read worker for the next fresh scan.
            if getattr(owner, '_closed', False) is True:
                self._close_reader()
            raise
        except BaseException:
            # A rejected read can close its worker permanently. Dispose it
            # without retrying this operation or an uncertain mutation.
            self._close_reader()
            raise

    def management(self):
        return ModDefinition('continent-flight', 'Continent Flight', version='0.4-fast-smooth2-test',
            description='Toggle flight on the current exploration character, then hold the configured ascend or descend key. Space remains jump. Travel resets flight. Bindings can be changed in Mod keybinds.',
            actions=(Action('status', 'Flight status', self.status),
                     Action('refresh', 'Find current exploration character', self.refresh),
                     Action('land', 'Leave flight', self.land)),
            keybinds=(Keybind('fly', 'Toggle flight (keep separate from jump)', ',', self.toggle),
                      Keybind('rise', 'Hold to ascend', 'E', self.rise),
                      Keybind('descend', 'Hold to descend', 'Q', self.descend)))

    def enable(self, session):
        if not getattr(session, 'supports_vector_values', False):
            raise RuntimeError('Continent Flight requires Vector support. Use the native Mods launcher (unified pause-menu runtime).')
        if not getattr(session, 'supports_scalar_assignment', False):
            raise RuntimeError('Fast flight requires the SDK scalar assignment runtime')
        self.session = session
        self.disabled = False
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
        LOG.info('Ready in %.1f ms: Comma toggles flight; Space remains jump', self.enable_ms)

    def refresh(self, _):
        self.discovery_generation += 1
        if self.flying:
            self.land(None)
        self.cached_observations = None
        self._prepare(use_cache=False)
        return self.local_status()

    def _prepare(self, *, use_cache):
        cached = self.cached_observations if use_cache else None
        started = time.perf_counter()
        failure = None
        try:
            with self.operation():
                self._prepare_calls(cached)
        except Exception as error:
            # The next explicit enable rediscovers; never reuse rejected data or
            # retry an invocation whose dispatch outcome could be uncertain.
            self.cached_observations = None
            failure = str(error)
            raise
        finally:
            self._diagnose_slow('prepare', started, failure)

    def _prepare_calls(self, cached, snapshot=None):
        catalog, pawn, movement = snapshot if snapshot is not None else discover_snapshot(
            self.session.pid, cached.catalog if cached else None)
        self.movement = movement
        self.movement_class = catalog.find_class('CharacterMovementComponent').index
        functions = {catalog.path_name(o): o for o in catalog.objects if o.class_name == 'Function'}
        if self.planner:
            self.planner.close()
        self.planner = self.session.invocation_planner(selected_results=True,
            **({'observations': cached} if cached else {'catalog': catalog}))
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
            'vertical_input': prepare('/Script/Engine.PawnMovementComponent:AddInputVector', target=movement,
                                      WorldVector={'X':0.0,'Y':0.0,'Z':0.0}, bForce=True),
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
        started = time.perf_counter()
        failure = None
        try:
            with self.operation():
                with self.calls[name].invoke() as result:
                    return result.return_value
        except InvocationError as error:
            failure = str(error)
            if error.native_error == 202 and error.outcome == 'not_dispatched':
                self._forget_target('Exploration character changed; waiting to rediscover')
            raise
        finally:
            self._diagnose_slow('invoke.' + name, started, failure)

    def _forget_target(self, reason):
        self.discovery_generation += 1
        self._restore_flight_tuning()
        # Revocation is local only: never call the destroyed pawn to clean up.
        self.flying = False
        self.direction = 0
        self.restore_mode = None
        self.cached_observations = None
        self.calls = {}
        self._close_reader()
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
        with self.operation():
            values = read_values(self.planner._catalog, self.movement).values
        mode = values.get((self.movement_class, 'MovementMode'))
        custom = values.get((self.movement_class, 'CustomMovementMode'))
        if type(mode) is not int or type(custom) is not int or mode in (0, 5):
            raise RuntimeError('Cannot capture a supported pre-flight movement mode')
        self.restore_mode = (mode, custom)
        self.calls['exit'] = self.calls['exit'].bind(NewMovementMode=mode, NewCustomMode=custom)
        try:
            self._apply_flight_tuning(values)
            self.invoke('enter')
        except Exception:
            self._restore_flight_tuning()
            raise
        self.flying = True
        self.last_poll = time.monotonic()
        LOG.info('Flight enabled for %s', self.pawn)
        return self.status(None)

    def _apply_flight_tuning(self, values):
        if self.flight_tuning:raise RuntimeError('Previous flight tuning still owns properties')
        for name in FLIGHT_TUNING:
            old=values.get((self.movement_class,name))
            if type(old) not in (int,float) or not math.isfinite(old):
                raise RuntimeError('Cannot capture flight property '+name)
        with self.operation():
            for name,value in FLIGHT_TUNING.items():
                old=values[(self.movement_class,name)]
                if old==value:continue
                self.session.assign_scalar(self.movement,name,value,expected=old,
                                           allow_mutation=True,catalog=self.planner._catalog)
                self.flight_tuning.append((self.movement,name,old,value))

    def _restore_flight_tuning(self):
        while self.flight_tuning:
            movement,name,old,value=self.flight_tuning[-1]
            with self.operation():
                # A transition may already have destroyed or recycled the old
                # component. Read live candidates, then match the full identity.
                c=capture_matching(self.session.pid,names=('CharMoveComp','Default__GameplayStatics'))
                observed=next((o for o in c.objects if (o.index,o.serial,o.address)==
                               (movement.index,movement.serial,movement.address)),None)
                if observed is None or observed.object_flags&0x40000030:
                    self.flight_tuning.pop();continue
                values=read_values(c,observed).values
                current=values.get((self.movement_class,name))
                if current==value:
                    self.session.assign_scalar(observed,name,old,expected=value,
                                               allow_mutation=True,catalog=c)
                elif current!=old:
                    LOG.warning('Flight restore preserved another writer: %s',name)
            self.flight_tuning.pop()
        self.vertical_profile=False

    def _set_vertical_profile(self, active):
        if active==self.vertical_profile:return
        # Input is consumed by engine ticks between controller polls. Avoid
        # braking ascent to a stop in those gaps; restore normal braking as
        # soon as the held vertical binding is released.
        with self.operation():
            for name,boost in VERTICAL_TUNING.items():
                value=boost if active else FLIGHT_TUNING[name]
                at=next((i for i,row in enumerate(self.flight_tuning) if row[1]==name),None)
                old,expected=(self.flight_tuning[at][2:] if at is not None else
                              (FLIGHT_TUNING[name],FLIGHT_TUNING[name]))
                if expected==value:continue
                self.session.assign_scalar(self.movement,name,value,expected=expected,
                                           allow_mutation=True,catalog=self.planner._catalog)
                row=(self.movement,name,old,value)
                if at is None:self.flight_tuning.append(row)
                else:self.flight_tuning[at]=row
        self.vertical_profile=active

    def space(self, _):
        if self.tap.press(time.monotonic()):
            self.toggle(None)

    def rise(self, _):
        self._begin_vertical('rise', 1)

    def descend(self, _):
        self._begin_vertical('descend', -1)

    def _vertical_key(self, binding):
        registry = self.session.mods
        selection = registry.select('continent-flight')
        key = registry.keybind(selection, binding)
        return None if key in registry.key_conflicts() else key

    def _begin_vertical(self, binding, direction):
        if self.flying:
            self.direction_key = self._vertical_key(binding)
            self.direction = direction if self.direction_key else 0

    def _vertical_held(self):
        binding = 'rise' if self.direction > 0 else 'descend'
        key = self._vertical_key(binding)
        # Remapping/unbinding revokes an already-held action; a fresh keydown
        # must start the new binding. Never fall back to hard-coded E/Q.
        return (key is not None and key == self.direction_key and
                bool(self.user32.GetAsyncKeyState(VIRTUAL_KEYS[key]) & 0x8000))

    def poll(self):
        now = time.monotonic()
        elapsed, self.last_poll = now - self.last_poll, now
        if self.disabled:
            return
        if not self.calls:
            if self.discovery_future is not None:
                if not self.discovery_future.done():
                    return
                future, self.discovery_future = self.discovery_future, None
                if self.discovery_pending_generation != self.discovery_generation:
                    return
                try:
                    snapshot = future.result()
                    with self.operation():
                        self._prepare_calls(None, snapshot)
                    LOG.info('Attached to current exploration character: %s; flight remains off', self.pawn)
                except Exception as exc:
                    if self.planner: self.planner.close()
                    self.planner = None
                    self.calls = {}
                    self.error = str(exc)
                self.next_discovery = now + 2.
                return
            if self.session is not None and now >= self.next_discovery:
                self.next_discovery = now + 2.
                if self.discovery_worker is None:
                    self.discovery_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='flight-discovery')
                self.discovery_pending_generation = self.discovery_generation
                # Capture PID on owner thread; worker never touches session/scope.
                self.discovery_future = self.discovery_worker.submit(discover_worker, self.session.pid)
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
        focused=pid.value==self.session.pid
        if not focused:
            self.direction = 0
        if self.direction:
            if not self._vertical_held():
                self.direction = 0
        try:
            if now>=self.next_flight_check:
                self.next_flight_check=now+.25
                if not self.invoke('controlled'):
                    self.land()
                    self._forget_target('Possession changed; waiting to rediscover')
                    return
                if not self.invoke('is_flying'):
                    self._restore_flight_tuning()
                    self.input_state['controlled_flight'] = False
                    self.flying=False;self.direction=0
                    return
            self.input_state['controlled_flight'] = True
            self._set_vertical_profile(bool(self.direction))
            if not focused:return
            # The movement component accelerates and brakes every engine frame.
            # Do not fight its speed cap with periodic velocity impulses.
            if self.direction:
                with self.operation():
                    with self.calls['vertical_input'].bind(
                            WorldVector={'X':0.0,'Y':0.0,'Z':float(self.direction)},bForce=True).invoke():
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
        self._restore_flight_tuning()
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

    def revoke_world(self,context):
        self.disabled=True;self.discovery_generation+=1
        self.input_state={};self.tap.last=None
        self._retirement_token=context.previous_token
        self._retirement_reader_closed=False
        if self.discovery_future is not None:self.discovery_future.cancel()

    def begin_world_retirement(self,context):
        return self.poll_world_retirement(context)

    def poll_world_retirement(self,context):
        if getattr(self,'_retirement_token',None)!=context.previous_token:return 'unknown'
        future=self.discovery_future
        if future is not None and not future.done():return 'pending'
        # Discovery workers only read. Never land or restore old movement
        # properties after the coordinator has retired their authoritative epoch.
        self.discovery_future=None
        if self.discovery_worker is not None:
            self.discovery_worker.shutdown(wait=False,cancel_futures=True)
            self.discovery_worker=None
        if self.planner is not None:self.planner.close();self.planner=None
        if not self._retirement_reader_closed:self._close_reader();self._retirement_reader_closed=True
        self.calls={};self.cached_observations=None;self.flight_tuning=[]
        self.flying=False;self.restore_mode=None;self.session=None
        return 'ack'

    def disable(self):
        self.disabled = True
        self.discovery_generation += 1
        if self.discovery_future is not None:
            self.discovery_future.cancel()
            self.discovery_future = None
        if self.discovery_worker is not None:
            # Any already-running task owns only a read context, and closes it
            # itself. Its result is discarded and can never invoke game code.
            self.discovery_worker.shutdown(wait=False, cancel_futures=True)
            self.discovery_worker = None
        try:
            self.land(None)
        finally:
            try:
                if self.planner:
                    self.planner.close()
            finally:
                self._close_reader()
                self.calls = {}
                self.planner = self.session = None
