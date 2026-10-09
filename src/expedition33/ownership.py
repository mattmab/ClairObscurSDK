"""Explicit, session-owned native UObject references for the experimental v7 backend.

Snapshots remain observations. A lease prevents ordinary GC collection while
owned; it does not prevent explicit engine destruction or replace identity checks.
No Python finalizer calls the game. Release explicitly or use a context manager.
"""
import weakref
from . import RuntimeQueryError


class LeaseError(RuntimeQueryError):
    def __init__(self, message, *, outcome, native_error=None):
        self.outcome = outcome
        self.native_error = native_error
        super().__init__(f'{message} (outcome={outcome}; do not retry unknown operations)')


class ObjectLease:
    """An explicit reference owned by one Session, optionally by one mod scope.

    ``object`` returns the original identity observation while this lease is
    active. ``release()`` returns True when acknowledged, False if GC requires
    deferred cleanup. Deferred leases are revoked immediately and retried only
    by the owning session's poll/close path. Dropping this Python value does not
    release native ownership; the session keeps it until release or shutdown.
    """
    def __init__(self, session, token, obj):
        self._session = weakref.ref(session)
        self._scope = None
        self._token = token
        self._object = obj
        self._state = 'active'

    @property
    def active(self):
        session = self._session()
        scope = self._scope() if self._scope is not None else None
        return (self._state == 'active' and session is not None and not session._closed and
                not getattr(session._transport, '_closed', False) and
                (self._scope is None or (scope is not None and not scope._closed)))

    @property
    def object(self):
        session = self._session()
        if session is None or not self.active:
            raise LeaseError('Object lease is no longer active', outcome=self._state)
        session._check()
        return self._object

    @property
    def release_pending(self):
        return self._state == 'pending_release'

    def release(self):
        session = self._session()
        if session is not None:
            session._transport._check_thread()
        if self._state == 'released':
            return True
        if self._state in ('unknown', 'invalid'):
            raise LeaseError('Lease release cannot be retried', outcome=self._state)
        if session is None or session._closed:
            raise LeaseError('Lease owner is unavailable', outcome='unknown')
        return session._release_lease(self)

    def __enter__(self):
        self.object
        return self

    def __exit__(self, *_exc):
        self.release()
