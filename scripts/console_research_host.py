"""Persistent console host for live validation. Stop via Ctrl+C or --seconds."""
import argparse
import json
import time
from dataclasses import asdict
from expedition33 import sdk

parser=argparse.ArgumentParser()
parser.add_argument('--seconds',type=int,default=300)
args=parser.parse_args()
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
