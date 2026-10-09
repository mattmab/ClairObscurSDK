"""Public SDK/Harness read-only getter proof. Requires cooperative host handover."""
import json
from pathlib import Path

from expedition33.catalog import capture
from expedition33.sdk import Session, TARGET
from expedition33._scope import SessionScope
from expedition33.introspection import Harness, UnsupportedCapability


def main():
    root = Path(__file__).resolve().parents[1]
    catalog = capture()
    def one(rows):
        rows = list(rows)
        assert len(rows) == 1
        return rows[0]
    pc = one(row for row in catalog.select('PlayerController') if not row.object_flags & 0x10)
    owner = catalog.find_class('Controller')
    function = one(row for row in catalog.objects if row.outer_index == owner.index and row.name == 'IsLocalController')
    request = {'op': 'invoke', 'target': {'$object': catalog.path_name(pc)},
               'member': 'IsLocalController', 'args': {}, 'allow_mutation': True}
    evidence = {'pid': catalog.pid, 'request': request, 'native_objects_retained': False}
    with Session(reflected=True) as session:
        result = session.invoke(pc, function)
        assert result.return_value is True and not result.outputs
        evidence['sdk'] = {'return': result.return_value, 'out': dict(result.outputs), 'outcome': result.outcome}
        scope = SessionScope(session)
        try:
            with Harness(session=scope) as harness:
                status = harness.request({'op': 'status'})
                assert 'invoke' in status['operations']
                for denied, error in (({**request, 'allow_mutation': False}, ValueError),
                                      ({**request, 'retain': 'owned'}, UnsupportedCapability)):
                    try: harness.request(denied)
                    except error: pass
                    else: raise AssertionError('Required mutation/ownership gate missing')
                evidence['harness'] = harness.request(request)
                assert evidence['harness'] is True
                evidence['harness_repeat'] = harness.request(request)
                assert evidence['harness_repeat'] is True
        finally:
            scope.close()
        assert session.call(session.find_object('Default__Actor'), TARGET) is False
        evidence['scope_cleanup_preserved_session'] = True
    evidence['session_closed'] = True
    (root / 'evidence/harness-invoke-live.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__': main()
