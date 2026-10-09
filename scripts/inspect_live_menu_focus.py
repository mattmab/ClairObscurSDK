"""Read-only reflected focus getters on the active main-menu subtree."""
import json
from pathlib import Path
from expedition33.catalog import capture
from expedition33._scope import SessionScope

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    catalog = capture()
    def one(rows):
        rows = list(rows)
        assert len(rows) == 1, len(rows)
        return rows[0]
    title = one(o for o in catalog.select('CommonActivatableWidget')
                if o.name == 'TitleScreen' and catalog.path_name(o).startswith('/Engine/Transient.'))
    pc = one(o for o in catalog.select('PlayerController') if not o.object_flags & 0x10)
    widget_class = catalog.find_class('Widget').index
    def function(owner, name):
        cls = catalog.find_class(owner).index
        return one(o for o in catalog.objects if o.outer_index == cls and o.name == name)
    keyboard, user = function('Widget', 'HasKeyboardFocus'), function('Widget', 'HasUserFocus')
    desired = function('CommonActivatableWidget', 'GetDesiredFocusTarget')
    candidates = [o for o in catalog.objects if widget_class in catalog.ancestors(o.class_index)
                  and title.index in {p.index for p in catalog.outer_chain(o)}]
    assert len(candidates) <= 96, 'Unexpectedly broad focus scan'
    evidence = dict(pid=session.pid, read_only=True, complete=False, candidate_count=len(candidates), widgets=[])
    def save():
        (ROOT / 'evidence/main-menu-focus.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    save()
    scope = SessionScope(session)
    try:
        with scope.invoke_retained(title, desired) as returned:
            evidence['desired_focus'] = capture().path_name(returned.return_value) if returned.return_value else None
        for obj in candidates:
            row = dict(path=catalog.path_name(obj), name=obj.name, class_name=obj.class_name,
                       keyboard=scope.invoke(obj, keyboard).return_value,
                       user=scope.invoke(obj, user, PlayerController=pc).return_value)
            evidence['widgets'].append(row)
            save()
    finally:
        scope.close()
    evidence['complete'] = True
    save()
    print('Main-menu focus scan:', [o['path'] for o in evidence['widgets'] if o['keyboard'] or o['user']])
    return evidence
