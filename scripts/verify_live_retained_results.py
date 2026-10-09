"""Public v8 and original Harness retention proof; requires host handover."""
import json
from pathlib import Path
import subprocess
import sys
import time

from expedition33.catalog import capture
from expedition33.sdk import Session
from expedition33._scope import SessionScope
from expedition33.introspection import Harness


def main():
    root = Path(__file__).resolve().parents[1]
    catalog = capture()
    def one(rows):
        rows = list(rows); assert len(rows) == 1; return rows[0]
    pc = one(o for o in catalog.select('PlayerController') if not o.object_flags & 0x10)
    cls = catalog.find_class('GameplayStatics')
    target = one(o for o in catalog.objects if o.name == 'Default__GameplayStatics' and o.class_index == cls.index)
    function = one(o for o in catalog.objects if o.outer_index == cls.index and o.name == 'GetPlayerController')
    def holders():
        subprocess.run([sys.executable, '-B', str(root/'scripts/inspect_gc_owners.py')], check=True, capture_output=True)
        data = json.loads((root/'evidence/gc-owners-live.json').read_text())
        return {h['holder_address']: (h['widget']['index'], h['widget']['serial'])
                for group in data['collections'] for h in group['strong_holders']}
    baseline = holders()
    evidence = {'pid': catalog.pid, 'baseline': baseline, 'new_objects_tested': False}
    with Session(retained=True) as session:
        a, b = SessionScope(session), SessionScope(session)
        def invoke(scope):
            return scope.invoke_retained(target, function, WorldContextObject=pc, PlayerIndex=0)
        first, peer = invoke(a), invoke(b)
        assert first.return_value.index == pc.index and peer.return_value.serial == pc.serial
        assert len(holders()) == len(baseline)+2
        a.close()
        assert not first.active and peer.active and len(holders()) == len(baseline)+1
        assert peer.release() and not peer.active and holders() == baseline
        b.close()
        with session.invoke_retained(target, function, WorldContextObject=pc, PlayerIndex=0) as owned:
            assert owned.return_value.index == pc.index
        assert holders() == baseline
        evidence['public_context_and_scope_cleanup'] = True
        scope = SessionScope(session)
        with Harness(scope) as harness:
            status = harness.request({'op': 'status'})
            assert 'release_value' in status['operations'] and '$value' in status['argument_types']
            request = dict(op='invoke', allow_mutation=True,
                           target={'$object': catalog.path_name(target)}, member='GetPlayerController',
                           args={'WorldContextObject': {'$object': catalog.path_name(pc)}, 'PlayerIndex': 0})
            result = harness.request(dict(request, retain='player'))
            assert result['$object'] == catalog.path_name(pc)
            assert len(holders()) == len(baseline)+1
            # Consume the original $value protocol while its native owner lives.
            result = harness.request(dict(request, args={'WorldContextObject': {'$value': {'name': 'player'}}, 'PlayerIndex': 0}))
            assert result['$object'] == catalog.path_name(pc)
            assert len(holders()) == len(baseline)+1 # Temporary call owner released after encoding.
            harness.request(dict(request, retain='player'))
            assert len(holders()) == len(baseline)+1 # Replacement removes old owner.
            released = harness.request({'op': 'release_value', 'name': 'player'})
            assert released['retained_values'] == [] and holders() == baseline
            evidence['harness_retain_value_argument_replacement_release'] = True
            harness.request(dict(request, retain='expiry'))
            started = time.monotonic()
            assert len(holders()) == len(baseline)+1
            print('Retained value active; checking original 60-second expiry while polling.', flush=True)
            while 'expiry' in harness._explorer.values and time.monotonic()-started < 65:
                harness.poll(); session.poll(); time.sleep(.05)
            elapsed = time.monotonic()-started
            assert 59 <= elapsed <= 65 and 'expiry' not in harness._explorer.values
            assert holders() == baseline
            evidence['original_expiry_seconds'] = elapsed
            harness.request(dict(request, retain='close'))
        assert holders() == baseline
        scope.close()
        leftover = session.invoke_retained(target, function, WorldContextObject=pc, PlayerIndex=0)
    assert not leftover.active and holders() == baseline
    evidence['harness_and_session_close_cleanup'] = True
    evidence['passed'] = True
    (root/'evidence/retained-results-live.json').write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__': main()
