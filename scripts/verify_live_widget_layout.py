"""Numeric struct invocation on retained SDK-owned widgets, no viewport or focus change.

Call run(sdk) from the existing v11 persistent Python console. The shared child
lifecycle probe releases the complete scope and verifies the holder baseline.
"""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def run(session):
    assert session.supports_pod_values
    def layout(scope, slot, button, catalog):
        def fn(owner, name):
            cls = catalog.find_class(owner)
            matches = [obj for obj in catalog.objects if obj.outer_index == cls.index and obj.name == name]
            assert len(matches) == 1, (owner, name, len(matches))
            return matches[0]
        def call(name, **arguments):
            return scope.invoke(slot, fn('CanvasPanelSlot', name), **arguments)
        # These values are exactly representable before and after the verified
        # double-to-float storage conversion in this build's slot setters.
        position, size = {'X':160.25,'Y':32.5}, {'X':640.0,'Y':360.0}
        call('SetPosition', InPosition=position)
        observed_position = dict(call('GetPosition').return_value)
        assert observed_position == position
        call('SetSize', InSize=size)
        observed_size = dict(call('GetSize').return_value)
        assert observed_size == size
        offsets = {'Left':120.0,'Top':80.0,'Right':500.0,'Bottom':300.0}
        call('SetOffsets', InOffset=offsets)
        # With zero anchors, margin components directly determine position/size.
        assert dict(call('GetPosition').return_value) == {'X':120.0,'Y':80.0}
        assert dict(call('GetSize').return_value) == {'X':500.0,'Y':300.0}
        anchors = {'Minimum':{'X':0.0,'Y':0.0},'Maximum':{'X':0.0,'Y':0.0}}
        call('SetAnchors', InAnchors=anchors)
        color = {'R':0.125,'G':0.25,'B':0.5,'A':1.0}
        scope.invoke(button, fn('Button','SetBackgroundColor'), InBackgroundColor=color)
        # Setter dispatch alone does not establish a rendered color or layout.
        return {'position_readback':observed_position,'size_readback':observed_size,
                'margin_position_size_readback':True, 'anchors_dispatch_returned':True,
                'color_dispatch_returned':True,'rendered':False}
    return runpy.run_path(str(ROOT/'scripts/verify_live_widget_children.py'))['run'](
        session, slot_probe=layout, evidence_name='widget-layout-live.json')
