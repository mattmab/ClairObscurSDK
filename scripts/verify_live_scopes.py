"""Run verify(sdk) in the existing trusted Python console; no new attachment.

py import runpy; runpy.run_path(r'D:/HobbyDevelopment/ClairObscurSDK/scripts/verify_live_scopes.py')['verify'](sdk)
"""
import json
from pathlib import Path

from expedition33._scope import SessionScope


def verify(session):
    first, second = SessionScope(session), SessionScope(session)
    events = [[], []]
    first_owner, second_owner = object(), object()
    before = set(session.console.dispatcher.command_names)
    try:
        first.console.register('sdk.scopetest.first', lambda _: 'first', owner=first_owner)
        second.console.register('sdk.scopetest.second', lambda _: 'second', owner=second_owner)
        first.console.expose('scope_test_first', first)
        actor = first.find_object('Default__Actor')
        target = 'Actor.IsActorBeingDestroyed'
        first.hook(actor, target, events[0].append)
        second.hook(actor, target, events[1].append)
        assert first.call(actor, target) is False
        first.poll()
        assert len(events[0]) == len(events[1]) == 1
        first.close()
        assert 'sdk.scopetest.first' not in session.console.dispatcher.command_names
        assert 'scope_test_first' not in session.console.dispatcher.namespace
        assert second.call(actor, target) is False
        second.poll()
        assert len(events[0]) == 1 and len(events[1]) == 2
        assert 'sdk.scopetest.second' in session.console.dispatcher.command_names
        try:
            first.call(actor, target)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Closed scope remained callable')
        second.close()
        assert set(session.console.dispatcher.command_names) == before
        assert session.call(actor, target) is False
        assert session.poll() == 0
        output = {'pid': session.pid, 'first_events': len(events[0]), 'second_events': len(events[1]),
                  'commands_restored': True, 'session_remains_usable': True,
                  'full_multi_mod_loader_live_tested': False}
        (Path(__file__).resolve().parents[1] / 'evidence/shared-scopes-live.json').write_text(
            json.dumps(output, indent=2), encoding='utf-8')
        return output
    finally:
        try:
            first.close()
        finally:
            second.close()
