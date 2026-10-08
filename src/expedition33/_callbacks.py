"""Python-side observer delivery. Transport and Unreal hook installation are separate.

Callbacks run on the dispatcher owner's Python thread, after native event copying.
They never run on the game thread and cannot alter or cancel an engine call.
"""
from collections import deque
from dataclasses import dataclass
import threading
import traceback
from typing import Callable
import weakref


@dataclass(frozen=True)
class ObservedIdentity:
    pid: int
    index: int
    serial: int
    name: str
    class_name: str


@dataclass(frozen=True)
class ObserverContext:
    sequence: int
    target: str
    object: ObservedIdentity
    game_thread_id: int
    result: bool


@dataclass(frozen=True)
class CallbackFailure:
    token: int
    target: str
    exception_type: str
    message: str
    traceback: str


class HookHandle:
    """Owns a Python subscription only; no native hook is implied by this type."""

    def __init__(self, dispatcher: 'CallbackDispatcher', token: int):
        self._dispatcher = weakref.ref(dispatcher)
        self._token = token

    @property
    def active(self) -> bool:
        dispatcher = self._dispatcher()
        return dispatcher is not None and dispatcher._is_active(self._token)

    def remove(self) -> None:
        dispatcher = self._dispatcher()
        if dispatcher is not None:
            dispatcher._remove(self._token)

    def __enter__(self) -> 'HookHandle':
        return self

    def __exit__(self, *_exc) -> None:
        self.remove()


class CallbackDispatcher:
    """Bounded subscriptions with deterministic, non-reentrant delivery.

    Removal during delivery prevents later callbacks in the same event. New
    subscriptions begin on the next event. A failing subscription is disabled;
    other subscribers still receive the event. close() releases all callbacks.
    Caller must separately stop the native producer before session shutdown.
    """

    def __init__(self):
        self._owner = threading.get_ident()
        self._subscriptions: dict[int, tuple[str, Callable[[ObserverContext], None]]] = {}
        self._next_token = 1
        self._delivering = False
        self._closed = False
        self._failures: deque[CallbackFailure] = deque(maxlen=64)
        self.failure_count = 0

    def _check_thread(self) -> None:
        if threading.get_ident() != self._owner:
            raise RuntimeError('Callbacks must be managed on their owning Python thread')

    def _is_active(self, token: int) -> bool:
        self._check_thread()
        return token in self._subscriptions

    def _remove(self, token: int) -> None:
        self._check_thread()
        self._subscriptions.pop(token, None)

    def subscribe(self, target: str, callback: Callable[[ObserverContext], None]) -> HookHandle:
        self._check_thread()
        if self._closed:
            raise RuntimeError('Callback dispatcher is closed')
        if not isinstance(target, str) or not target or not callable(callback):
            raise ValueError('A target name and callable are required')
        if len(self._subscriptions) >= 256:
            raise RuntimeError('Callback subscription limit reached')
        token = self._next_token
        self._next_token += 1
        self._subscriptions[token] = (target, callback)
        return HookHandle(self, token)

    def deliver(self, context: ObserverContext) -> int:
        self._check_thread()
        if self._closed:
            return 0
        if self._delivering:
            raise RuntimeError('Recursive event delivery is not supported')
        if not isinstance(context, ObserverContext):
            raise TypeError('Expected a copied ObserverContext')
        self._delivering = True
        attempted = 0
        try:
            for token in tuple(self._subscriptions):
                subscription = self._subscriptions.get(token)
                if subscription is None or subscription[0] != context.target:
                    continue
                target, callback = subscription
                attempted += 1
                try:
                    callback(context)
                except BaseException as error:
                    # This is an explicit mod isolation boundary, including
                    # SystemExit. Do not retain exception objects or frames.
                    self._subscriptions.pop(token, None)
                    self.failure_count += 1
                    try:
                        message = str(error)
                        trace = ''.join(traceback.format_exception(error))
                    except BaseException:
                        message, trace = '<exception formatting failed>', ''
                    self._failures.append(CallbackFailure(token, target,
                        type(error).__name__, message[:4096], trace[-16384:]))
        finally:
            self._delivering = False
        return attempted

    def failures(self) -> tuple[CallbackFailure, ...]:
        self._check_thread()
        return tuple(self._failures)

    def close(self) -> None:
        self._check_thread()
        self._closed = True
        self._subscriptions.clear()
