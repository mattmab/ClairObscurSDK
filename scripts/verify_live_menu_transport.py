"""Bounded v14 transport smoke: no widget creation, attachment or focus changes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33 import sdk, _menu_wire


def main():
    evidence = {'scope': 'v14 transport and empty menu status/close only', 'complete': False}
    path = ROOT / 'evidence/menu-transport-live.json'
    def save():
        path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    save()
    try:
        for relative in ('build/runtime-session-v14/runtime_session_v14.dll', 'build/research-probe-v14/research_probe.exe'):
            evidence[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        with sdk.Session(menu_ownership=True) as session:
            transport = session._transport
            evidence['snapshot'] = transport.start
            evidence['menu_protocol'] = transport.menu_protocol
            evidence['ping'] = transport.command('ping')
            sent = _menu_wire.request('status', 1)
            response = transport.command('menu', sent)
            reply = _menu_wire.decode(sent, response['menu_packet'])
            evidence['menu_status'] = dict(error=reply.error, outcome=reply.outcome, active=reply.active)
            assert reply.error == 0 and reply.outcome == 'returned' and not reply.active
            save()
        evidence['normal_close'] = True
        evidence['complete'] = True
        save()
        print(json.dumps(evidence, indent=2))
    except BaseException as error:
        evidence['error'] = repr(error)
        save()
        raise


if __name__ == '__main__':
    main()
