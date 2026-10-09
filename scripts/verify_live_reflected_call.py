"""Isolated v6 getter specimen. Stop the existing SDK host cooperatively first.

Does not create widgets, alter input modes, or install console hooks. Native
dispatch return is tested separately from the specimen's expected boolean value.
"""
from dataclasses import replace
import json
from pathlib import Path

from expedition33.catalog import capture
from expedition33.invocation import prepare_call
from expedition33._invocation_wire import encode_plan, decode_reply
from expedition33._session import SessionTransport


def main():
    root = Path(__file__).resolve().parents[1]
    catalog = capture()
    def one(rows):
        rows = list(rows)
        assert len(rows) == 1, [(row.index, row.name) for row in rows]
        return rows[0]
    pc = one(row for row in catalog.select('PlayerController') if not row.object_flags & 0x10)
    owner = catalog.find_class('Controller')
    function = one(row for row in catalog.objects if row.outer_index == owner.index and row.name == 'IsLocalController')
    plan = prepare_call(catalog, pc, function, {})
    assert plan.parameter_size == 1 and plan.return_offset == 0 and not plan.objects
    session = SessionTransport(_executable=root / 'build/research-probe-v6/research_probe.exe')
    records = []
    try:
        assert session.reflected_protocol == 1 and session.start['pid'] == catalog.pid
        for label, specimen, expected in (
            ('stale_identity', replace(plan, target=replace(pc, serial=pc.serial + 1)), 202),
            ('changed_layout', replace(plan, function_flags=plan.function_flags ^ 1), 204),
            ('getter', plan, 0),
            ('getter_repeat', plan, 0),
        ):
            request = encode_plan(specimen)
            response = session.command('reflected-invoke', request)
            reply = decode_reply(request, response['call_packet'])
            records.append({'case': label, 'outcome': reply.outcome, 'error': reply.error,
                            'data': reply.data.hex(), 'closed': response['closed']})
            assert reply.error == expected, records[-1]
            if expected:
                assert reply.outcome == 'not_dispatched'
            else:
                assert reply.outcome == 'dispatch_returned' and reply.data == b'\x01'
            assert session.command('ping')['closed'] is False
    finally:
        session.close()
        result = {'pid': catalog.pid, 'target': catalog.path_name(pc),
                  'function': catalog.path_name(function), 'cases': records,
                  'session_closed': True, 'widget_creation_tested': False}
        (root / 'evidence/reflected-call-live.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
