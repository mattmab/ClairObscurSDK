"""One-time orderly handover for the older run_sdk loop without request_stop.

Run request() in its trusted in-game Python console. This changes only that
launcher's local time binding so its next loop condition exits. It neither
mutates the time module nor closes transport underneath the active callback.
The launcher's existing context manager performs normal mod/session cleanup.
"""
import math
from pathlib import Path
from types import SimpleNamespace
import time


def request():
    import __main__
    expected = Path(__file__).resolve().with_name('run_sdk.py')
    if Path(__main__.__file__).resolve() != expected:
        raise RuntimeError('This handover is only for the known run_sdk.py host')
    if __main__.time is not time:
        raise RuntimeError('Launcher time binding already changed; inspect before retrying')
    names = __main__.main.__code__.co_names
    if not all(name in names for name in ('monotonic', 'sleep', 'ModLoader')):
        raise RuntimeError('Unrecognized launcher loop; no handover applied')
    __main__.time = SimpleNamespace(monotonic=lambda: math.inf, sleep=time.sleep)
    return 'Orderly handover requested. The current command returns before mod/session cleanup.'
