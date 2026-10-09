"""Reusable planning observations with unchanged native dispatch validation.

These are not UObject owners or trusted engine addresses. Native code checks
identities, function/schema/argument constraints and execution context for every
dispatch. Object outputs still receive same-call native leases and fresh
identity observations before exposure. An explicit selected-results mode combines
fresh closures with older planning rows; it does not refresh untouched objects.
Scalar/text outputs need no new full catalog.
"""
import weakref
import threading

from .invocation import UnsupportedInvocation


class InvocationPlanner:
    def __init__(self, session, *, scope=None, selected_results=False):
        session._check()
        if type(selected_results) is not bool:
            raise ValueError('selected_results must be bool')
        self._selected_results = selected_results
        if not session.supports_retained_invocation:
            raise UnsupportedInvocation('Prepared calls require retained invocation support')
        self._session = weakref.ref(session)
        self._owner = threading.get_ident()
        self._scope = weakref.ref(scope) if scope is not None else None
        self._closed = False
        self._generation = 0
        self._catalog = None
        self.refresh()

    def _check(self):
        if self._closed:
            raise RuntimeError('Invocation planner is closed')
        session = self._session()
        if session is None:
            raise RuntimeError('Invocation session no longer exists')
        session._check()
        if self._scope is not None:
            scope = self._scope()
            if scope is None:
                raise RuntimeError('Invocation resource scope no longer exists')
            scope._check()
        return session

    def refresh(self):
        session = self._check()
        # A failed refresh also revokes older plans. Never silently fall back.
        self._generation += 1
        self._catalog = None
        from .catalog import capture
        catalog = capture()
        if catalog.pid != session.pid:
            raise ValueError('Planning catalog belongs to another process')
        self._catalog = catalog

    def refresh_from(self, catalog):
        """Adopt an explicit catalog observation and revoke existing plans.

        This performs no read and makes no freshness claim beyond the supplied
        observation. Useful when an SDK read discovered additional child objects.
        Native dispatch validation remains mandatory.
        """
        session = self._check()
        self._generation += 1
        self._catalog = None
        from .catalog import Catalog
        if not isinstance(catalog, Catalog) or catalog.pid != session.pid:
            raise ValueError('Expected a catalog from this process')
        self._catalog = catalog

    def prepare(self, obj, function, **arguments):
        session = self._check()
        if self._catalog is None:
            raise RuntimeError('Refresh the planner before preparing calls')
        from .invocation import prepare_call
        plan = prepare_call(self._catalog, obj, function, arguments,
            pod_values=session.supports_pod_values, text_values=session.supports_text_values,
            enum_values=session.supports_enum_values)
        return PreparedInvocation(self, plan)

    def close(self):
        # Idempotent local revocation; no engine state or object ownership.
        if threading.get_ident() != self._owner:
            raise RuntimeError('Planner cleanup requires the owning Python thread')
        if self._closed:
            return
        self._closed = True
        self._generation += 1
        self._catalog = None

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *_error):
        # Clear observations even when the session has faulted or exited.
        self.close()


class PreparedInvocation:
    def __init__(self, planner, plan):
        self._planner = weakref.ref(planner)
        self._generation = planner._generation
        self._plan = plan

    def _check(self):
        planner = self._planner()
        if planner is None:
            raise RuntimeError('Keep the invocation planner alive while using prepared calls')
        session = planner._check()
        if self._generation != planner._generation or planner._catalog is None:
            raise RuntimeError('Prepared invocation was revoked by planner refresh')
        return planner, session

    def bind(self, **arguments):
        """Make a new argument snapshot using this planner's shared catalog.

        Function metadata is described again; this does not reuse a stale schema
        as authority. The original prepared call remains unchanged.
        """
        planner, _ = self._check()
        return planner.prepare(self._plan.target, self._plan.function, **arguments)

    def invoke(self, *, refresh_from_result=False):
        """Optionally reuse the validated object-result catalog for future plans.

        This revokes all existing plans before dispatch. A failed operation leaves
        the planner empty, so a caller must explicitly refresh before proceeding.
        Scalar-only success reuses the input catalog; it does not claim freshness.
        """
        if type(refresh_from_result) is not bool:
            raise ValueError('refresh_from_result must be bool')
        planner, session = self._check()
        scope = planner._scope() if planner._scope is not None else None
        if planner._scope is not None and scope is None:
            raise RuntimeError('Invocation resource scope no longer exists')
        catalog = planner._catalog
        if refresh_from_result:
            planner._generation += 1
            planner._catalog = None
        result, observed = session._invoke_retained_plan(
            self._plan, catalog, _return_catalog=True,
            _selected_results=planner._selected_results)
        if scope is not None:
            # Hold scope alive through dispatch and use the existing adoption path.
            scope._adopt_retained(result)
        if refresh_from_result:
            planner._catalog = observed
        return result
