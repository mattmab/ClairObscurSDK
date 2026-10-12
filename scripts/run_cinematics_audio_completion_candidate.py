"""Widget ownership candidate; full playback remains gated on live isolation tests."""
from pathlib import Path
import sys
import time
import logging
import argparse
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import expedition33.sdk as sdk
from expedition33.mods import ModLoader
from expedition33.settings import SettingsStore
from expedition33._reader import ReadBatch
from expedition33.controller_commands import CommandServer
from expedition33.workflow_telemetry import Telemetry
from cinematics_controller_commands import commands

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--lease-limit',type=int,default=1024)
parser.add_argument('--lease-owner-quota',type=int,default=256)
parser.add_argument('--lease-cleanup-reserve',type=int,default=64)
args=parser.parse_args()
# Validate before attaching to the game.
from expedition33.lease_policy import request as lease_request
lease_request(1,args.lease_limit,args.lease_owner_quota,args.lease_cleanup_reserve)

# Keep the sparse Slate-user validation, cached layout and Escape handling from
# the currently validated menu candidate. v24 predates those fixes.
original_transport = sdk.SessionTransport

def candidate_transport(*, _executable=None):
    if _executable is None or _executable.parent.name != 'research-probe-v24-multi-pause':
        raise ValueError('Cinematics requires the multiple pause-entry controller')
    transport = original_transport(_executable=ROOT / 'build/research-probe-v52-audiocompletion/research_probe.exe')
    if any(getattr(transport, capability, 0) != 1 for capability in (
            'audio_cleanup_diagnostics_protocol', 'cinematic_widget_animation_protocol',
            'cinematic_widget_diagnostics_protocol', 'cinematic_sound_diagnostics_protocol')):
        transport.close()
        raise RuntimeError('Missing v52 ownership and route diagnostics')
    if (getattr(transport, 'cinematic_widget_protocol', 0) != 1 or getattr(transport, 'media_owner_protocol', 0) != 1 or getattr(transport, 'string_value_protocol', 0) != 1 or
            getattr(transport, 'pause_attachment_protocol', 0) != 2 or
            getattr(transport, 'blueprint_trace_protocol', 0) != 1):
        transport.close()
        raise RuntimeError('Missing Cinematics menu candidate capabilities')
    return transport

sdk.SessionTransport = candidate_transport

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / 'logs/cinematics.log', encoding='utf-8')])

# End the failed read context before independent mod shutdown operations.
with sdk.Session(multiple_pause_entries=True) as session, ModLoader(
        ROOT / 'mods', settings=SettingsStore(ROOT / 'settings/management.json'), session=session) as loader, ReadBatch(session.pid, share=True):
    from expedition33.lease_policy import configure
    logging.info('Native lease policy: %s', configure(session,hard_limit=args.lease_limit,
        owner_quota=args.lease_owner_quota,cleanup_reserve=args.lease_cleanup_reserve))
    for name in ('SDKManagement', 'IntrospectionHarness', 'Cinematics'):
        loader.load(name)
        loader.enable(name, console=True)
    loader._loaded['SDKManagement'][1].prepare()
    telemetry = Telemetry(ROOT / 'logs/workflow.jsonl')
    session._transport._workflow_telemetry = telemetry
    server = CommandServer(commands(session, loader, telemetry),
        capabilities={'inspect', 'menu', 'playback_stop', 'lifecycle', 'research_component'}, telemetry=telemetry)
    try:
        connection = server.write_connection(ROOT / 'settings/controller')
        logging.info('Structured controller connection file: %s', connection)
        telemetry.record('controller.start', 'lifecycle', time.time(), 0, True, controller_restarts=1)
        while not loader.stop_requested:
            server.poll()
            loader.poll()
            telemetry.poll_wait(.005)
        time.sleep(.3)  # Bounded grace for the client to read the shutdown acknowledgement.
    finally:
        server.close()
        session._transport._workflow_telemetry = None
        telemetry.close()









