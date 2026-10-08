"""Persistent console host for live validation. Stop via Ctrl+C or --seconds."""
import argparse
import json
import time
from pathlib import Path
from dataclasses import asdict
from expedition33 import sdk
from expedition33.mods import ModLoader

parser=argparse.ArgumentParser()
parser.add_argument('--seconds',type=int,default=300)
parser.add_argument('--mod', action='store_true')
args=parser.parse_args()
if args.mod:
    with ModLoader(Path(__file__).resolve().parents[1] / 'mods') as loader:
        loader.load('ConsoleExample')
        loader.enable('ConsoleExample', console=True)
        print('CONSOLE_MOD_READY', flush=True)
        deadline=time.monotonic()+args.seconds
        try:
            while time.monotonic()<deadline:
                loader.poll('ConsoleExample')
                time.sleep(.05)
        except KeyboardInterrupt:
            pass
    print('CONSOLE_MOD_CLOSED', flush=True)
    raise SystemExit(0)
with sdk.Session() as session:
    session.console.enable()
    session.console.write('Independent Expedition 33 SDK: py commands are ready.')
    print('CONSOLE_READY',flush=True)
    deadline=time.monotonic()+args.seconds
    try:
        while time.monotonic()<deadline:
            for result in session.console.poll():
                print(json.dumps(asdict(result)),flush=True)
            time.sleep(.05)
    except KeyboardInterrupt:
        pass
print('CONSOLE_CLOSED',flush=True)
