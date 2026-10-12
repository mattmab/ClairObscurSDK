"""Bounded live retention stress; no gameplay functions or object mutations."""
import json
from pathlib import Path
from expedition33._scope import SessionScope
from expedition33.catalog import capture_matching
from expedition33.lease_policy import statistics
from expedition33.ownership import LeaseError

def run(session):
    report={'before':statistics(session)}
    catalog=capture_matching(session.pid,names=('Default__Actor',))
    targets=[obj for obj in catalog.objects if obj.name=='Default__Actor' and obj.class_name=='Actor']
    if len(targets)!=1:raise RuntimeError('Expected one static Actor default')
    scope=SessionScope(session,lease_owner='lease-validation')
    try:
        leases=[scope.retain(targets[0]) for _ in range(report['before']['quota'])]
        report['at_quota']=statistics(session)
        try:scope.retain(targets[0])
        except LeaseError as error:
            report['quota_rejection']={'native_error':error.native_error,'outcome':error.outcome}
        else:raise AssertionError('Owner exceeded quota')
        old=leases.pop();token=old._token;assert old.release()
        replacement=scope.retain(targets[0])
        assert replacement._token>token
        report['reuse_monotonic']=True
        report['after_rejection']=statistics(session)
    finally:scope.close()
    report['after']=statistics(session)
    assert report['after']['active']==report['before']['active']
    report['baseline_restored']=True
    path=Path(__file__).resolve().parents[1]/'evidence/lease-growth-live.json'
    path.write_text(json.dumps(report,indent=2))
    return report
