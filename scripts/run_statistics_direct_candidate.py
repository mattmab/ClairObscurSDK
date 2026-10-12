"""Explicit v26 layout-batch candidate launcher; production launcher stays v23."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import expedition33.sdk as sdk

original_transport = sdk.SessionTransport

def candidate_transport(*, _executable=None):
    if _executable is None or _executable.parent.name != 'research-probe-v23-pause-vector':
        raise ValueError('Layout candidate requires the pause/Vector controller')
    transport = original_transport(_executable=ROOT / 'build/research-probe-v26-statistics/research_probe.exe')
    if getattr(transport, 'blueprint_trace_protocol', 0) != 1:
        transport.close()
        raise RuntimeError('Missing Blueprint trace capability')
    return transport

sdk.SessionTransport = candidate_transport
sys.argv = [str(ROOT / 'scripts/run_sdk.py'), 'management', '--keybinds', '--pause-menu', '--shared-reader']
runpy.run_path(sys.argv[0], run_name='__main__')


