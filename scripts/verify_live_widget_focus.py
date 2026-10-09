"""Visible owned CommonUI child focus transfer to/from a confirmed game widget.

Requires an explicit current focus-owner path from live getter observations.
Does not change input mode, install callbacks, or activate game menu actions.
"""
import json
from pathlib import Path
import runpy

from expedition33.catalog import capture
from expedition33._scope import SessionScope

ROOT = Path(__file__).resolve().parents[1]


def run(session, prior_path):
    catalog = capture()
    prior = catalog.find_path(prior_path, 'Widget')
    pc = [o for o in catalog.select('PlayerController') if not o.object_flags & 0x10]
    assert len(pc) == 1
    pc = pc[0]
    owner = catalog.find_class('Widget').index
    def function(name):
        matches = [o for o in catalog.objects if o.outer_index == owner and o.name == name]
        assert len(matches) == 1
        return matches[0]
    keyboard, user = function('HasKeyboardFocus'), function('HasUserFocus')
    set_keyboard, set_user = function('SetKeyboardFocus'), function('SetUserFocus')
    progress = dict(pid=session.pid, passed=False, prior_path=prior_path, input_mode_changed=False)
    def save():
        (ROOT / 'evidence/widget-focus-progress.json').write_text(json.dumps(progress, indent=2), encoding='utf-8')
    scope = SessionScope(session)
    try:
        prior_lease = scope.retain(prior)
        prior = prior_lease.object
        def focused(target):
            return dict(keyboard=scope.invoke(target, keyboard).return_value,
                        user=scope.invoke(target, user, PlayerController=pc).return_value)
        progress['before'] = focused(prior)
        save()
        assert progress['before'] == dict(keyboard=True, user=True), 'No confirmed focus owner; nothing displayed'
        def on_display(widget_scope, widget, button, player):
            assert focused(prior) == progress['before'], 'Game focus changed while constructing the specimen'
            transferred = False
            try:
                scope.invoke(button, set_user, PlayerController=player)
                transferred = True
                scope.invoke(button, set_keyboard)
                progress['owned_child'] = focused(button)
                progress['prior_during'] = focused(prior)
                save()
                assert progress['owned_child'] == dict(keyboard=True, user=True)
                assert progress['prior_during'] == dict(keyboard=False, user=False)
            finally:
                if transferred:
                    scope.invoke(prior, set_user, PlayerController=player)
                    scope.invoke(prior, set_keyboard)
                    progress['restored_before_removal'] = focused(prior)
                    save()
                    assert progress['restored_before_removal'] == progress['before']
            return dict(focus_transferred=True, prior_restored=True)
        result = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_visible.py'))['run'](
            session, activatable=True, button_enabled=True, on_display=on_display,
            hold_seconds=20, label_text='SDK focus lifecycle test', evidence_name='widget-focus-live.json')
        progress['after_removal'] = focused(prior)
        assert progress['after_removal'] == progress['before']
        progress['inner_holder_cleanup'] = result['holder_baseline_restored']
    finally:
        scope.close()
        save()
    progress['passed'] = True
    save()
    print('Owned visible CommonUI child acquired focus; prior game focus restored before and after menu removal.')
    return progress
