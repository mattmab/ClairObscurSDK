"""Arm an observer, then await normal user/GUI game exit. Never kills the game."""
import ctypes
import argparse
from ctypes import wintypes
import json
from pathlib import Path
import time
from expedition33 import sdk, RuntimeQueryError

kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
parser = argparse.ArgumentParser()
parser.add_argument('--console', action='store_true')
args = parser.parse_args()
session = sdk.Session()
actor = session.find_object('Default__Actor')
process = kernel.OpenProcess(0x100000 | 0x1000, False, actor.pid)
assert process, ctypes.get_last_error()
events = []
try:
    if args.console:
        session.console.enable()
        session.console.register('sdk.exitproof', lambda _: 'exit proof', owner=session)
    hook = session.hook(actor, sdk.TARGET, events.append)
    session.call(actor, sdk.TARGET)
    assert session.poll() == 1 and hook.active
    print(json.dumps({'armed': True, 'pid': actor.pid, 'hook_active': hook.active}), flush=True)
    deadline = time.monotonic() + 300
    while True:
        status = kernel.WaitForSingleObject(process, 1000)
        if status == 0:
            break
        assert status == 258 and time.monotonic() < deadline, 'Game exit wait failed or timed out'
    exit_code = wintypes.DWORD()
    assert kernel.GetExitCodeProcess(process, ctypes.byref(exit_code))
    failure = None
    try:
        session.call(actor, sdk.TARGET)
    except RuntimeQueryError as error:
        failure = str(error)
    assert failure, 'Exited target did not fail closed'
    session.close()
    assert not hook.active
    result = {'pid': actor.pid, 'exit_code': exit_code.value, 'transport_failure': failure,
              'console_attached_before_exit': args.console,
              'console_namespace_cleared': not session.console.dispatcher.namespace,
              'python_cleanup': True, 'pre_exit_callbacks': len(events)}
    filename = 'console-game-exit.json' if args.console else 'game-exit.json'
    (Path(__file__).resolve().parents[1] / 'evidence' / filename).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    assert exit_code.value == 0, 'Game did not exit normally; inspect crash evidence'
finally:
    kernel.CloseHandle(process)
    session.close()
