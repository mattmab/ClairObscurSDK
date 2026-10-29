"""Bounded known frontend rejection evidence; no exception text or traceback."""
from dataclasses import dataclass
from .invocation import InvocationError
from .multi_controls import ControlBindBatchRejected
from ._metadata_stabilization import UnstableUIIdentity


@dataclass(frozen=True)
class FrontendRejection:
    kind: str
    native_error: int
    outcome: str
    completed: int | None = None
    role: str | None = None


def known_rejection(error):
    from .menu import MenuError
    if (isinstance(error,MenuError) and error.outcome=='returned'
            and error.native_error in (901,90220) and error.active is False):
        return FrontendRejection('MenuFocusUnavailable',error.native_error,'returned')
    if isinstance(error,UnstableUIIdentity):
        return FrontendRejection('UnstableUIIdentity',0,'not_dispatched',role=error.role)
    if (isinstance(error,InvocationError) and error.outcome=='not_dispatched'
            and error.native_error==202):
        return FrontendRejection('InvocationError',202,'not_dispatched')
    if (isinstance(error,ControlBindBatchRejected) and error.outcome=='returned'
            and type(error.completed) is int and 1<=error.completed<=48
            and error.native_error in (1010,1011,1012,1013)):
        return FrontendRejection('ControlBindBatchRejected',error.native_error,
            'returned',error.completed)
    return None
