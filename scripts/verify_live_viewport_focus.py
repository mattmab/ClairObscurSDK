"""Single-user viewport -> owned Button -> same viewport focus specimen.

Uses the persistent owner thread and verified reflected setters. No input-mode
changes or bindings. Research-only: no disconnect restoration guarantee.
"""
import json
from pathlib import Path
import runpy

from expedition33.catalog import capture

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    observe = runpy.run_path(str(ROOT/'scripts/inspect_slate_focus_dispatch.py'))['observe']
    progress = dict(pid=session.pid, passed=False, input_mode_changed=False,
                    restoration_attempted=False, mutation_outcome_unknown=False)
    def save():
        (ROOT/'evidence/viewport-focus-progress.json').write_text(
            json.dumps(progress, indent=2), encoding='utf-8')
    def supported(state):
        assert state['pid'] == session.pid
        assert state['registered_viewport_matches_game_viewport']
        assert len(state['users']) == 1 and state['users'][0]['index'] == 0
        assert state['users'][0].get('strong_count', 0) > 0
        assert state['game_viewport']['vtable'] == '0x6e78128'
        assert state['keyboard_user_query'] == '0x10044d0'
    baseline = observe()
    progress['before'] = baseline
    save()
    supported(baseline)
    assert baseline['users'][0]['matches_game_viewport'], 'Current owner is not the game viewport'
    catalog = capture()
    def function(owner, name):
        cls = catalog.find_class(owner).index
        rows = [o for o in catalog.objects if o.outer_index == cls and o.name == name]
        assert len(rows) == 1
        return rows[0]
    library_cls = catalog.find_class('WidgetBlueprintLibrary').index
    library = [o for o in catalog.objects if o.class_index == library_cls
               and o.name == 'Default__WidgetBlueprintLibrary']
    assert len(library) == 1
    set_focus = function('Widget', 'SetUserFocus')
    keyboard, user = function('Widget', 'HasKeyboardFocus'), function('Widget', 'HasUserFocus')
    restore = function('WidgetBlueprintLibrary', 'SetFocusToGameViewport')
    def same_viewport(state):
        supported(state)
        assert state['application'] == baseline['application']
        assert state['game_viewport'] == baseline['game_viewport']
        assert state['users'][0]['address'] == baseline['users'][0]['address']
    def on_display(scope, widget, button, player):
        before = observe()
        same_viewport(before)
        assert before['users'][0]['matches_game_viewport'], 'Focus changed during construction'
        acknowledged = False
        try:
            progress['mutation_outcome_unknown'] = True
            save()
            scope.invoke(button, set_focus, PlayerController=player)
            acknowledged = True
            progress['mutation_outcome_unknown'] = False
            progress['owned_child'] = dict(
                keyboard=scope.invoke(button, keyboard).return_value,
                user=scope.invoke(button, user, PlayerController=player).return_value)
            during = observe()
            progress['during'] = during
            save()
            same_viewport(during)
            assert progress['owned_child'] == dict(keyboard=True, user=True)
            assert not during['users'][0]['matches_game_viewport']
        finally:
            # A failed/unknown setter is never replayed. Restore only after an
            # acknowledged transfer and revalidation of the single-user target.
            if acknowledged:
                same_viewport(observe())
                progress['restoration_attempted'] = True
                progress['mutation_outcome_unknown'] = True
                save()
                scope.invoke(library[0], restore)
                progress['mutation_outcome_unknown'] = False
                after = observe()
                progress['restored_before_removal'] = after
                save()
                same_viewport(after)
                assert after['users'][0]['matches_game_viewport']
                assert scope.invoke(button, keyboard).return_value is False
                assert scope.invoke(button, user, PlayerController=player).return_value is False
        return dict(focus_transferred=True, viewport_restored=True)
    result = runpy.run_path(str(ROOT/'scripts/verify_live_widget_visible.py'))['run'](
        session, activatable=True, button_enabled=True, on_display=on_display,
        hold_seconds=0, label_text='SDK focus test', evidence_name='viewport-focus-live.json')
    final = observe()
    progress['after_removal'] = final
    save()
    same_viewport(final)
    assert final['users'][0]['matches_game_viewport']
    assert result['holder_baseline_restored'] and result['passed']
    progress['holder_baseline_restored'] = progress['passed'] = True
    save()
    print('Single-user viewport/owned Button focus transfer, restoration and exact cleanup passed.')
    return progress
