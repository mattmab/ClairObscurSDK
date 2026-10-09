"""Isolated v8 getter test. Cooperatively stop the persistent host first.

Uses an existing PlayerController; does not create widgets or force GC.
"""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

from expedition33.catalog import capture
from expedition33.invocation import prepare_call, decode_result
from expedition33 import _retained_wire as wire, _lease_wire as leases
from expedition33._session import SessionTransport


def main():
    root = Path(__file__).resolve().parents[1]
    catalog = capture()
    def one(rows):
        rows = list(rows); assert len(rows) == 1; return rows[0]
    pc = one(o for o in catalog.select('PlayerController') if not o.object_flags & 0x10)
    cls = catalog.find_class('GameplayStatics')
    target = one(o for o in catalog.objects if o.name == 'Default__GameplayStatics' and o.class_index == cls.index)
    function = one(o for o in catalog.objects if o.outer_index == cls.index and o.name == 'GetPlayerController')
    plan = prepare_call(catalog, target, function, {'WorldContextObject': pc, 'PlayerIndex': 0})
    null_plan = prepare_call(catalog, target, function, {'WorldContextObject': pc, 'PlayerIndex': -1})
    assert plan.parameter_size == 24 and plan.return_offset == 16 and plan.entry_rva == 0x373a480
    def holders():
        subprocess.run([sys.executable, '-B', str(root/'scripts/inspect_gc_owners.py')], check=True, capture_output=True)
        data = json.loads((root/'evidence/gc-owners-live.json').read_text())
        return {h['holder_address']: (h['widget']['index'], h['widget']['serial'])
                for group in data['collections'] for h in group['strong_holders']}
    baseline = holders()
    records = []
    session = SessionTransport(_executable=root/'build/research-probe-v8/research_probe.exe')
    def lease_command(command, **kwargs):
        request = leases.request(command, **kwargs)
        response = session.command(command, request)
        reply = leases.decode(command, request, response['lease_packet'])
        assert reply.outcome == 'completed' and not reply.error
        return reply
    def invoke(specimen):
        request = wire.encode_plan(specimen)
        try:
            response = session.command('retained-invoke', request)
            reply, tokens = wire.decode_reply(request, response['retained_packet'])
            if reply.outcome == 'unknown': raise RuntimeError('Unknown outcome; no retry')
            return reply, tokens
        except BaseException:
            session._abort()
            raise
    try:
        assert session.retained_protocol == 1 and session.start['pid'] == catalog.pid
        reply, tokens = invoke(replace(plan, target=replace(target, serial=target.serial+1)))
        assert reply.outcome == 'not_dispatched' and reply.error == 202 and not tokens
        assert lease_command('lease-status').active == 0
        records.append({'case': 'stale_target', 'outcome': reply.outcome, 'error': reply.error})
        reply, tokens = invoke(plan)
        result = decode_result(plan, reply, capture())
        assert result.return_value.index == pc.index and result.return_value.serial == pc.serial
        assert len(tokens) == 1 and tokens[0][0] == 16
        assert {offset for offset, *_ in reply.objects} == {0, 16}
        assert lease_command('lease-status').active == 1
        held = holders()
        added = {key: value for key, value in held.items() if key not in baseline}
        assert len(added) == 1 and next(iter(added.values())) == (pc.index, pc.serial)
        records.append({'case': 'object_return', 'outcome': reply.outcome, 'leases': tokens, 'holders': added,
                        'input_reference_not_retained': True})
        lease_command('lease-release', token=tokens[0][1])
        assert holders() == baseline
        reply, tokens = invoke(null_plan)
        assert decode_result(null_plan, reply, capture()).return_value is None and not tokens
        assert lease_command('lease-status').active == 0
        records.append({'case': 'null_return', 'outcome': reply.outcome, 'leases': tokens})
        reply, tokens = invoke(plan)
        assert reply.outcome == 'dispatch_returned' and len(tokens) == 1
        records.append({'case': 'session_owned_cleanup', 'leases': tokens})
    finally:
        session.close()
    assert holders() == baseline
    result = {'passed': True, 'pid': catalog.pid, 'function': catalog.path_name(function),
              'cases': records, 'baseline_restored': True, 'new_object_creation_tested': False,
              'forced_gc_tested': False, 'python_public_retained_api_tested': False}
    (root/'evidence/retained-call-live.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
