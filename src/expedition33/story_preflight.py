"""Explicitly retryable observations during uncommitted story preparation."""
from . import RuntimeQueryError


class PreflightReadDeferred(RuntimeQueryError):
    """A selected external read failed; no native call was attempted by it."""


def observe(reader,*args,**kwargs):
    # Call only with a known external read/schema-planning operation. Never
    # wrap asset loading, lease acquisition, setters or retained invocations.
    try:return reader(*args,**kwargs)
    except PreflightReadDeferred:raise
    except RuntimeQueryError as error:
        if getattr(error,'outcome',None) is not None:raise
        raise PreflightReadDeferred(str(error)) from error
