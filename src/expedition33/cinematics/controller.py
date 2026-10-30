"""Owner-thread replay lifecycle, independent of engine adapters and UI.

Factories only construct Python wrappers. Native preparation/dispatch belongs
in adapter.start(), after the wrapper is retained and presentation is ready.
Adapters explicitly normalize their backend; truthiness is never an outcome.
"""
from dataclasses import dataclass
from enum import Enum
import threading
from typing import Protocol


class StartResult(Enum):
    STARTED = 'started'
    REJECTED = 'rejected'
    UNKNOWN = 'unknown'


class StopResult(Enum):
    STOPPED = 'stopped'
    DEFERRED = 'deferred'
    UNKNOWN = 'unknown'


class BackendState(Enum):
    ACTIVE = 'active'
    COMPLETE = 'complete'
    FAILED = 'failed'
    UNKNOWN = 'unknown'


class ControllerState(Enum):
    IDLE = 'idle'
    QUEUED = 'queued'
    STARTING = 'starting'
    ACTIVE = 'active'
    OBSERVING = 'observing'
    STOPPING = 'stopping'
    CLEANUP_PENDING = 'cleanup_pending'
    UNCERTAIN = 'uncertain'
    DISABLED = 'disabled'


@dataclass(frozen=True)
class ReplayObservation:
    state: BackendState
    detail: str = ''


@dataclass(frozen=True)
class CleanupRequest:
    epoch_valid: bool
    reason: str
    generation: int


@dataclass(frozen=True)
class ReplaySnapshot:
    state: ControllerState
    generation: int
    intent_id: int
    selection_id: str | None
    enabled: bool
    busy: bool
    engine_owned: bool
    detail: str


class ReplayAdapter(Protocol):
    def start(self) -> StartResult: ...
    def status(self) -> ReplayObservation: ...
    def poll(self) -> ReplayObservation: ...
    def stop(self) -> StopResult: ...
    def close(self, request: CleanupRequest) -> bool: ...


class ReplayBusy(RuntimeError):
    pass


def _epoch(value):
    # Callers supply immutable copied world/controller identities, never live
    # engine wrappers or a mutable context dictionary.
    if type(value) in (str, int) or value is None:
        return value
    if type(value) is tuple:
        return tuple(_epoch(item) for item in value)
    raise ValueError('Replay epoch must be an immutable copied token')


class ReplayController:
    def __init__(self):
        self._thread = threading.get_ident()
        self._state = ControllerState.IDLE
        self._enabled = True
        self._disable_requested = False
        self._generation = 0
        self._intent_id = 0
        self._selection = None
        self._epoch = None
        self._epoch_revoked = False
        self._factory = None
        self._adapter = None
        self._engine_owned = False
        self._detail = ''
        self._cleanup_reason = ''
        self._cleanup_unknown = False
        self._callback_depth = 0

    def _check(self, *, mutation=False):
        if threading.get_ident() != self._thread:
            raise RuntimeError('Replay callbacks require the controller owner thread')
        if mutation and self._callback_depth:
            raise RuntimeError('Replay callbacks cannot reenter lifecycle mutations')

    def _invoke(self, callback, *args):
        self._check()
        self._callback_depth += 1
        try:
            return callback(*args)
        finally:
            self._callback_depth -= 1

    def status(self):
        self._check()
        return ReplaySnapshot(self._state, self._generation, self._intent_id,
                              self._selection, self._enabled, self._busy(),
                              self._engine_owned, self._detail)

    def _busy(self):
        return self._factory is not None or self._adapter is not None

    def queue(self, selection_id, factory, epoch, *, engine_owned=False, intent_id=None):
        self._check(mutation=True)
        if not self._enabled or self._disable_requested:
            raise ReplayBusy('Replay controller is disabling or disabled')
        if self._busy():
            raise ReplayBusy('An earlier replay still owns its lifecycle')
        if type(selection_id) is not str or not 1 <= len(selection_id) <= 512:
            raise ValueError('A bounded replay selection ID is required')
        if not callable(factory) or type(engine_owned) is not bool:
            raise ValueError('A wrapper factory and explicit ownership policy are required')
        if intent_id is not None and (type(intent_id) is not int or intent_id <= 0):
            raise ValueError('Selection intent ID must be a positive integer')
        if intent_id is not None and intent_id <= self._intent_id:
            raise ValueError('Selection intent ID was already handled or superseded')
        epoch = _epoch(epoch)
        self._generation += 1
        self._intent_id = self._intent_id + 1 if intent_id is None else intent_id
        self._selection, self._factory, self._epoch = selection_id, factory, epoch
        self._epoch_revoked = False
        self._engine_owned = engine_owned
        self._cleanup_unknown = False
        self._cleanup_reason = self._detail = ''
        self._state = ControllerState.QUEUED
        return self._generation

    def _released(self):
        self._adapter = self._factory = None
        self._cleanup_unknown = False
        self._cleanup_reason = ''
        if self._disable_requested:
            self._enabled = False
        self._state = ControllerState.IDLE if self._enabled else ControllerState.DISABLED

    def _cleanup(self, epoch_valid, reason):
        if self._adapter is None:
            self._released()
            return True
        if self._cleanup_unknown:
            return False
        self._state = ControllerState.CLEANUP_PENDING
        self._cleanup_reason = reason
        try:
            result = self._invoke(self._adapter.close,
                                  CleanupRequest(epoch_valid, reason, self._generation))
            if type(result) is not bool:
                raise TypeError('Adapter cleanup must acknowledge with an exact bool')
        except Exception as error:
            self._cleanup_unknown = True
            self._state = ControllerState.UNCERTAIN
            self._detail = 'Cleanup outcome unknown: ' + str(error)
            return False
        if not result:
            return False
        self._released()
        return True

    @staticmethod
    def _observation(value):
        if (type(value) is not ReplayObservation or type(value.state) is not BackendState or
                type(value.detail) is not str):
            raise TypeError('Adapter must return a typed ReplayObservation')
        return value

    def poll(self, current_epoch, *, presentation_ready=True):
        self._check(mutation=True)
        current_epoch = _epoch(current_epoch)
        if type(presentation_ready) is not bool:
            raise ValueError('Presentation readiness requires an exact bool')
        if not self._busy():
            return self.status()
        valid = not self._epoch_revoked and current_epoch == self._epoch
        if not valid:
            self._epoch_revoked = True
            self._detail = 'World/controller epoch replaced; replay continuation revoked'
            # A revoked adapter must release only proven retired SDK tracking.
            # It must never compensate camera/input/pawn state in the old world.
            self._cleanup(False, 'epoch_replaced')
            return self.status()
        if self._state is ControllerState.CLEANUP_PENDING:
            self._cleanup(True, self._cleanup_reason)
            return self.status()
        if self._state is ControllerState.UNCERTAIN:
            # Read-only observation may prove eventual terminal ownership; it
            # never repeats start/stop or a lost cleanup acknowledgement.
            if not self._cleanup_unknown:
                try:
                    observed = self._observation(self._invoke(self._adapter.status))
                except Exception:
                    return self.status()
                if observed.detail:
                    self._detail = observed.detail
                if observed.state in (BackendState.COMPLETE, BackendState.FAILED):
                    self._cleanup(True, observed.state.value)
            return self.status()
        if self._state is ControllerState.QUEUED:
            if not presentation_ready:
                return self.status()
            self._state = ControllerState.STARTING
            try:
                adapter = self._invoke(self._factory)
                if adapter is None:
                    raise TypeError('Replay factory returned no adapter')
                self._adapter = adapter
                self._factory = None
                result = self._invoke(adapter.start)
                if type(result) is not StartResult:
                    raise TypeError('Adapter start must return StartResult')
            except Exception as error:
                import logging
                logging.getLogger(__name__).exception('Cinematic backend startup failed')
                self._detail = 'Replay startup failed: ' + str(error)
                if self._adapter is None:
                    # The factory contract permits no native operations.
                    self._released()
                else:
                    self._state = ControllerState.UNCERTAIN
                return self.status()
            if result is StartResult.UNKNOWN:
                self._state = ControllerState.UNCERTAIN
                self._detail = 'Replay start outcome unknown; dispatch will not be retried'
            elif result is StartResult.REJECTED:
                self._detail = 'Replay start was rejected'
                self._cleanup(True, 'start_rejected')
            else:
                self._state = ControllerState.ACTIVE
            return self.status()
        if self._state is ControllerState.STOPPING:
            self._stop_owned()
            if self._state is ControllerState.CLEANUP_PENDING:
                self._cleanup(True, self._cleanup_reason)
            return self.status()
        try:
            observed = self._observation(self._invoke(self._adapter.poll))
        except Exception as error:
            self._detail = 'Replay polling failed: ' + str(error)
            if self._engine_owned:
                self._state = ControllerState.UNCERTAIN
            else:
                self._cleanup(True, 'poll_failed')
            return self.status()
        if observed.detail:
            self._detail = observed.detail
        if observed.state is BackendState.UNKNOWN:
            self._state = ControllerState.UNCERTAIN
            if not observed.detail:
                self._detail = 'Replay state unknown; continuation is blocked'
        elif observed.state in (BackendState.COMPLETE, BackendState.FAILED):
            self._cleanup(True, observed.state.value)
        return self.status()

    def _stop_owned(self):
        try:
            result = self._invoke(self._adapter.stop)
            if type(result) is not StopResult:
                raise TypeError('Adapter stop must return StopResult')
        except Exception as error:
            self._state = ControllerState.UNCERTAIN
            self._detail = 'Replay stop outcome unknown: ' + str(error)
            return
        if result is StopResult.UNKNOWN:
            self._state = ControllerState.UNCERTAIN
            self._detail = 'Replay stop outcome unknown; stop will not be retried'
        elif result is StopResult.DEFERRED:
            self._state = ControllerState.STOPPING
        else:
            self._state = ControllerState.CLEANUP_PENDING
            self._cleanup_reason = 'stopped'

    def request_stop(self, current_epoch):
        self._check(mutation=True)
        valid = not self._epoch_revoked and _epoch(current_epoch) == self._epoch
        if not self._busy():
            return True
        if not valid:
            self._epoch_revoked = True
            return self._cleanup(False, 'epoch_replaced')
        if self._adapter is None:
            self._detail = 'Queued replay cancelled before preparation'
            self._released()
            return True
        if self._cleanup_unknown:
            return False
        if self._state is ControllerState.CLEANUP_PENDING:
            return self._cleanup(True, self._cleanup_reason)
        if self._engine_owned:
            # No campaign Stop, synthesized completion or destruction. Continue
            # observing until the original engine owner reports completion.
            if self._state is not ControllerState.UNCERTAIN:
                self._state = ControllerState.OBSERVING
            self._detail = 'Original engine playback must finish before cleanup'
            return False
        if self._state is ControllerState.UNCERTAIN:
            return self._cleanup(True, 'uncertain_owned_cleanup')
        self._stop_owned()
        if self._state is ControllerState.CLEANUP_PENDING:
            return self._cleanup(True, self._cleanup_reason)
        return False

    def close(self, current_epoch):
        """Disable only after acknowledged cleanup; False retains the owner."""
        self._check(mutation=True)
        current_epoch = _epoch(current_epoch)
        self._disable_requested = True
        if not self._busy():
            self._released()
            return True
        return self.request_stop(current_epoch)

    def enable(self):
        self._check(mutation=True)
        if self._busy():
            raise ReplayBusy('Cannot enable a controller with unresolved cleanup')
        self._enabled = True
        self._disable_requested = False
        self._state = ControllerState.IDLE
