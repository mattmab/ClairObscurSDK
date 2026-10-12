"""Read-only ownership accounting for the current persistent SDK controller."""
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parents[1]
def run(session,loader):
    owners={id(record[2]):name for name,record in loader._loaded.items() if record[2] is not None}
    def owner(scope):
        while scope is not None:
            if id(scope) in owners:return owners[id(scope)]
            scope=scope._parent() if scope._parent is not None else None
        return 'session'
    rows=[]
    for lease in session._leases:
        obj=lease._object
        scope=lease._scope() if lease._scope else None
        rows.append(dict(token=lease._token,state=lease._state,owner=owner(scope),
            index=obj.index,serial=obj.serial,address=obj.address,name=obj.name,class_name=obj.class_name))
    rows.sort(key=lambda row:row['token'])
    if len(rows)>4096:raise RuntimeError('Lease audit bound exceeded')
    native=asdict(session._lease_command('lease-status'))
    counts=Counter((r['index'],r['serial'],r['address']) for r in rows)
    report=dict(timestamp=time.time(),pid=session.pid,native=native,python_tracked=len(rows),
        by_owner=dict(Counter(r['owner'] for r in rows)),by_class=dict(Counter(r['class_name'] for r in rows)),
        duplicate_hold_count=sum(n-1 for n in counts.values()),
        observations='Python lease identities and native active count; not a fresh validity/GC proof.',rows=rows)
    growing=getattr(session._transport,'lease_policy_protocol',0)==1
    if growing:
        from expedition33.lease_policy import statistics
        from expedition33.catalog import capture_selected
        report['policy']=statistics(session)
        # A bounded identity refresh distinguishes retained live slots from
        # stale Python records. This does not prove GC reachability by parents.
        if rows:
            capture_selected(session.pid,tuple(dict.fromkeys(
                (row['index'],row['serial'],row['address']) for row in rows)))
        report['fresh_identity_validation']='all retained object selectors matched'
    destination='lease-audit-after.json' if growing else 'lease-audit-before.json'
    (ROOT/'evidence'/destination).write_text(json.dumps(report,indent=2))
    return {key:value for key,value in report.items() if key!='rows'}
