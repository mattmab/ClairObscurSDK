"""Reuse an enclosing read worker without nesting ownership contexts."""
from contextlib import contextmanager
from expedition33._reader import ReadBatch, active_reader

@contextmanager
def reads(pid):
    current = active_reader()
    if current is not None:
        current._check()
        if current.pid != pid:
            raise RuntimeError('Builder read context belongs to another process')
        yield current
    else:
        with ReadBatch(pid) as reader:
            yield reader
