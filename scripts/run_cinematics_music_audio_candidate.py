"""Native Cinematics browser candidate; replay remains blocked pending isolation."""
from pathlib import Path
import sys
import time
import logging
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import expedition33.sdk as sdk
from expedition33.mods import ModLoader
from expedition33.settings import SettingsStore
from expedition33._reader import ReadBatch

# Keep the sparse Slate-user validation, cached layout and Escape handling from
# the currently validated menu candidate. v24 predates those fixes.
original_transport = sdk.SessionTransport

def candidate_transport(*, _executable=None):
    if _executable is None or _executable.parent.name != 'research-probe-v24-multi-pause':
        raise ValueError('Cinematics requires the multiple pause-entry controller')
    transport = original_transport(_executable=ROOT / 'build/research-probe-v37-musicaudio/research_probe.exe')
    if (getattr(transport, 'media_owner_protocol', 0) != 1 or getattr(transport, 'string_value_protocol', 0) != 1 or
            getattr(transport, 'pause_attachment_protocol', 0) != 2 or
            getattr(transport, 'blueprint_trace_protocol', 0) != 1):
        transport.close()
        raise RuntimeError('Missing Cinematics menu candidate capabilities')
    return transport

sdk.SessionTransport = candidate_transport

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / 'logs/cinematics.log', encoding='utf-8')])

with sdk.Session(multiple_pause_entries=True) as session, ReadBatch(session.pid, share=True), ModLoader(
        ROOT / 'mods', settings=SettingsStore(ROOT / 'settings/management.json'), session=session) as loader:
    for name in ('SDKManagement', 'IntrospectionHarness', 'Cinematics'):
        loader.load(name)
        loader.enable(name, console=True)
    loader._loaded['SDKManagement'][1].prepare()
    while not loader.stop_requested:
        loader.poll()
        time.sleep(.005)




