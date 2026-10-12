"""Cached ownership/callback evidence only; this performs no engine/transport calls."""
def snapshot(menu):
    panel = menu.panel
    native = panel.menu
    controls = getattr(native, '_controls', None)
    frame = menu.frame
    return {
        'panel_state': panel.state,
        'panel_uncertain': panel.uncertain,
        'native_state': getattr(native, '_state', None),
        'accept_input': menu._accept_input,
        'presentation_suspended': menu._presentation_suspended,
        'presentation_state': getattr(getattr(menu, '_presentation_owner', None), 'state', None),
        'failure': menu.failure,
        'view_closed': menu.view.closed,
        'frame_revision': getattr(frame, 'revision', None),
        'event_sequence': getattr(controls, 'sequence', None),
        'dropped_events': getattr(controls, 'dropped_events', None),
        'actions': [dict(state=action._state, registration=action._registration,
                         failures=list(action.failures)) for action in menu.actions],
        'rows': [dict(index=index, label=control.label, enabled=control.enabled)
                 for index, control in enumerate(frame.controls)] if frame else [],
    }
