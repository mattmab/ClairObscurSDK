"""Isolated v7 ownership specimen. Cooperatively stop the persistent host first.

Retains an already game-owned controller, not a created object. Proves native
registration/release, not collection survival or full Harness retention parity.
"""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time

from expedition33.catalog import capture
from expedition33._session import SessionTransport
from expedition33 import _lease_wire as wire


def main():
    root=Path(__file__).resolve().parents[1]
    catalog=capture()
    matches=[o for o in catalog.select('PlayerController') if not o.object_flags & 0x10]
    assert len(matches)==1
    pc=matches[0]
    records=[]
    executable=root/'build/research-probe-v7/research_probe.exe'
    def owners():
        subprocess.run([sys.executable,'-B',str(root/'scripts/inspect_gc_owners.py')],check=True,capture_output=True,text=True)
        data=json.loads((root/'evidence/gc-owners-live.json').read_text())
        return [h for group in data['collections'] for h in group['strong_holders']]
    baseline=owners()
    def command(session,verb,**kwargs):
        sent=wire.request(verb,**kwargs)
        raw=session.command(verb,sent)
        reply=wire.decode(verb,sent,raw['lease_packet'])
        records.append({'command':verb,'error':reply.error,'outcome':reply.outcome,
                        'active':reply.active,'token':reply.token})
        assert reply.outcome=='completed'
        return reply
    evidence={'pid':catalog.pid,'object':catalog.path_name(pc),'baseline_holders':len(baseline),'cases':records,
              'gc_survival_tested':False,'widget_creation_tested':False}
    session=None
    try:
        session=SessionTransport(_executable=executable)
        assert session.lease_protocol==1
        assert command(session,'lease-status').active==0
        bad=command(session,'lease-acquire',object=replace(pc,serial=pc.serial+1))
        assert bad.error==404 and bad.active==0 and bad.token==0
        first=command(session,'lease-acquire',object=pc)
        second=command(session,'lease-acquire',object=pc)
        assert not first.error and not second.error and first.token!=second.token and second.active==2
        held=owners()
        added=[h for h in held if h['holder_address'] not in {b['holder_address'] for b in baseline}]
        assert len(added)==2 and all(h['widget']['index']==pc.index and h['widget']['serial']==pc.serial for h in added)
        evidence['observed_holders']=added
        assert command(session,'lease-release',token=first.token).active==1
        assert command(session,'lease-release',token=first.token).error==402
        session.close(); session=None
        assert len(owners())==len(baseline)
        evidence['normal_close_removed_remaining_holder']=True
        session=SessionTransport(_executable=executable)
        assert command(session,'lease-status').active==0
        assert command(session,'lease-release',token=second.token).error==402
        third=command(session,'lease-acquire',object=pc)
        assert not third.error and third.token>second.token
        # Deliberately exit only this candidate's controller subprocess. Its
        # target-owned watcher must perform cleanup on the game thread.
        session._abort(); session=None
        for attempt in range(5):
            after=owners()
            if len(after)==len(baseline): break
            time.sleep(0.2)
        assert len(after)==len(baseline)
        evidence['controller_exit_removed_holder']=True
        session=SessionTransport(_executable=executable)
        assert command(session,'lease-status').active==0
        assert session.command('ping')['closed'] is False
        session.close(); session=None
        evidence['reconnected_after_controller_exit']=True
        evidence['passed']=True
    finally:
        if session is not None: session.close()
        (root/'evidence/leases-live.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence,indent=2))


if __name__=='__main__': main()
