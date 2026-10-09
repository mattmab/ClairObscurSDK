"""Public/scoped lease proof; requires cooperative persistent-host handover."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

from expedition33.catalog import capture
from expedition33.sdk import Session
from expedition33._scope import SessionScope
from expedition33.ownership import LeaseError


def main():
    root=Path(__file__).resolve().parents[1]
    catalog=capture()
    def one(rows):
        rows=list(rows); assert len(rows)==1; return rows[0]
    pc=one(o for o in catalog.select('PlayerController') if not o.object_flags & 0x10)
    cls=catalog.find_class('Controller')
    getter=one(o for o in catalog.objects if o.outer_index==cls.index and o.name=='IsLocalController')
    def holders():
        subprocess.run([sys.executable,'-B',str(root/'scripts/inspect_gc_owners.py')],check=True,capture_output=True,text=True)
        data=json.loads((root/'evidence/gc-owners-live.json').read_text())
        return {h['holder_address']:(h['widget']['index'],h['widget']['serial'])
                for group in data['collections'] for h in group['strong_holders']}
    baseline=holders()
    evidence={'pid':catalog.pid,'object':catalog.path_name(pc),'baseline':baseline,
              'invocation_output_retention_tested':False,'gc_survival_tested':False}
    with Session(leases=True) as session:
        a,b=SessionScope(session),SessionScope(session)
        try:
            assert a.supports_object_leases and b.supports_reflected_invocation
            first=a.retain(pc); second=b.retain(pc)
            held=holders()
            added={key:value for key,value in held.items() if key not in baseline}
            assert len(added)==2 and all(value==(pc.index,pc.serial) for value in added.values())
            evidence['two_independent_scoped_holders']=added
            a.close()
            assert not first.active and second.active
            after=holders()
            assert len(after)==len(baseline)+1 and all(after.get(k)==v for k,v in baseline.items())
            assert b.invoke(second.object,getter).return_value is True
            evidence['other_mod_and_invocation_survive_scope_close']=True
            try: _=first.object
            except LeaseError: pass
            else: raise AssertionError('Closed scope lease remains accessible')
            b.close()
            assert holders()==baseline
            with session.retain(pc) as lease:
                assert lease.active and lease.object==pc
            assert not lease.active and lease.release() is True
            try: session.retain(replace(pc,serial=pc.serial+1))
            except LeaseError as error:
                assert error.native_error==404
                evidence['stale_serial_rejected']=True
            else: raise AssertionError('Stale native identity accepted')
            leftover=session.retain(pc)
        finally:
            a.close(); b.close()
    assert not leftover.active and leftover.release() is True
    assert holders()==baseline
    evidence['context_manager_and_session_cleanup']=True
    evidence['passed']=True
    (root/'evidence/python-leases-live.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence,indent=2))


if __name__=='__main__': main()
