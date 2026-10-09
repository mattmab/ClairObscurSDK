"""v16 connection and absent-owner rejection only; never binds a button."""
import dataclasses
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33 import sdk, _button_action_wire as wire, _menu_wire


def main():
    evidence={'scope':'v16 handshake, empty menu and absent-owner rejection', 'complete':False}
    path=ROOT/'evidence/button-action-transport-live.json'
    def save(): path.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    save()
    try:
        for relative in ('build/runtime-session-v16/runtime_session_v16.dll','build/research-probe-v16/research_probe.exe'):
            evidence[relative]=hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
        with sdk.Session(button_actions=True) as session:
            transport=session._transport
            assert session.supports_button_actions
            evidence['snapshot']=transport.start
            evidence['protocol']=transport.button_action_protocol
            evidence['session_nonce']=transport.button_action_session
            sent=_menu_wire.request('status',1)
            response=transport.command('menu',sent)
            menu=_menu_wire.decode(sent,response['menu_packet'])
            assert menu.error==0 and not menu.active and response['button_reference_state']==0
            sent=wire.request('status',1,1)
            response=transport.command('button-action',sent)
            reply=wire.decode(sent,response['button_action_packet'],session=transport.button_action_session)
            assert reply.error==911 and reply.outcome=='returned' and reply.state==0 and not reply.events
            evidence['absent_owner_status']=dataclasses.asdict(reply)
            evidence['ping']=transport.command('ping')
            save()
        evidence.update(normal_close=True,complete=True)
        save()
        print('v16 live transport passed; absent owner rejected, no button hook installed, normal close.')
    except BaseException as error:
        evidence['error']=repr(error); save(); raise


if __name__=='__main__': main()
