"""Fixed, bounded read-only getters on the current owned cinematic menu.

No caller-selected targets, function names, addresses, or getter arguments.
Call only on the controller owner thread; this does dispatch engine getters.
"""
from expedition33.catalog import capture_matching, capture_selected
from expedition33.enums import EnumValue


def _identity(obj):
    return dict(pid=obj.pid, index=obj.index, serial=obj.serial, address=hex(obj.address))


def probe_owned_menu(menu):
    panel, frame = menu.panel, menu.frame
    if panel.state != 'open' or panel.uncertain or panel.menu is None:
        raise RuntimeError('Probe requires a known open owned menu')
    matches = [i for i, c in enumerate(frame.controls) if c.label == 'Close']
    if len(matches) != 1 or matches[0] >= len(panel.buttons):
        raise RuntimeError('Expected exactly one current Close control')
    close_index = matches[0]
    button = panel.buttons[close_index]
    scope = panel.scope
    scope._check()
    specs = (
        ('close', button, 'Widget', 'IsHovered'),
        ('close', button, 'Widget', 'HasKeyboardFocus'),
        ('close', button, 'Widget', 'GetVisibility'),
        ('close', button, 'Widget', 'GetIsEnabled'),
        ('panel', panel.widget, 'UserWidget', 'IsInViewport'),
        ('panel', panel.widget, 'CommonActivatableWidget', 'IsActivated'),
        ('panel', panel.widget, 'Widget', 'GetVisibility'),
        ('panel', panel.widget, 'Widget', 'GetIsEnabled'),
        ('primary', panel.buttons[0], 'Widget', 'HasKeyboardFocus'),
    )
    names = tuple(sorted({s[2] for s in specs} | {s[3] for s in specs} | {'ESlateVisibility'}))
    catalog = capture_matching(scope.pid, names=names)
    targets = {obj.index: obj for _, obj, _, _ in specs}
    catalog = catalog.with_observations(capture_selected(scope.pid,
        tuple((obj.index, obj.serial, obj.address) for obj in targets.values())))
    planner = scope.invocation_planner(catalog=catalog, selected_results=True)
    result = dict(close_index=close_index, frame_revision=frame.revision,
        identities={name: _identity(obj) for name, obj, _, _ in specs}, getters={}, errors={})
    try:
        plans = []
        for name, obj, owner_name, function_name in specs:
            key = name + '.' + function_name
            try:
                owner = catalog.find_class(owner_name)
                functions = [o for o in catalog.objects if o.outer_index == owner.index and
                    o.name == function_name and o.class_name == 'Function']
                if len(functions) != 1:
                    raise RuntimeError('Expected one exact reflected getter')
                plans.append((key, planner.prepare(obj, functions[0])))
            except (ValueError, KeyError, RuntimeError) as error:
                result['errors'][key] = repr(error)
        for key, plan in plans:
            if menu.panel is not panel or menu.frame is not frame or panel.state != 'open' or panel.uncertain:
                raise RuntimeError('Menu changed during bounded getter probe')
            # Exceptions end the probe; never retry an uncertain invocation.
            with plan.invoke() as invocation:
                value = invocation.return_value
                if isinstance(value, EnumValue):
                    value = dict(name=value.name, value=value.value)
                elif type(value) is not bool:
                    raise RuntimeError('Unexpected copied getter result')
                result['getters'][key] = value
        return result
    finally:
        planner.close()
