"""Render-only suspension of an existing owned menu; input lifetime is retained.

No visibility, focus, activation, parent or native menu ownership is changed.
The same menu must gate button callbacks while _presentation_suspended is true.
"""
import math
from expedition33.catalog import capture_matching, capture_selected
from expedition33.values import read_values


class MenuPresentation:
    def __init__(self, menu):
        self.menu = menu
        self.panel = menu.panel
        self.state = 'new'
        self.planner = self.hide_call = self.restore_call = None
        self.original_opacity = None

    def prepare(self):
        if self.state != 'new' or self.panel.state != 'open' or self.panel.uncertain:
            raise RuntimeError('Prepare visual suspension only for a known open owned menu')
        if self.menu.panel is not self.panel or getattr(self.menu, '_presentation_owner', None) is not None:
            raise RuntimeError('Menu presentation is already owned or changed')
        scope = self.panel.scope
        scope._check()
        catalog = capture_matching(scope.pid, names=('Widget', 'SetRenderOpacity'))
        widget = self.panel.widget
        catalog = catalog.with_observations(capture_selected(scope.pid, ((widget.index, widget.serial, widget.address),)))
        owner = catalog.by_index[catalog.find_class('Widget').index]
        functions = [o for o in catalog.objects if o.outer_index == owner.index and o.name == 'SetRenderOpacity' and o.class_name == 'Function']
        if len(functions) != 1:
            raise RuntimeError('Verified render-opacity setter is unavailable')
        values = read_values(catalog, widget)
        key = (owner.index, 'RenderOpacity')
        opacity = values.values.get(key)
        if (values.types.get(key) != 'FloatProperty' or key in values.errors or key in values.truncated or
                type(opacity) is not float or not math.isfinite(opacity) or not 0. <= opacity <= 1.):
            raise RuntimeError('Current owned menu render opacity is not verified')
        self.original_opacity = opacity
        self.planner = scope.invocation_planner(catalog=catalog, selected_results=True)
        # Planner validates the actual reflected parameter name/type/signature.
        self.hide_call = self.planner.prepare(widget, functions[0], InOpacity=0.)
        self.restore_call = self.planner.prepare(widget, functions[0], InOpacity=opacity)
        self.state = 'prepared'
        return self

    @staticmethod
    def _invoke(prepared):
        with prepared.invoke():
            pass

    def suspend(self):
        if self.state != 'prepared' or self.menu.panel is not self.panel or self.panel.state != 'open' or self.panel.uncertain:
            raise RuntimeError('Menu visual suspension is not prepared')
        if getattr(self.menu, '_presentation_owner', None) is not None:
            raise RuntimeError('Menu presentation already has an owner')
        self.menu._presentation_owner = self
        self.menu._presentation_suspended = True
        self.state = 'unknown'
        self.panel._mutate(self._invoke, self.hide_call)
        self.state = 'suspended'

    def restore(self):
        if self.state == 'restored':
            return
        if self.state == 'unknown':
            raise RuntimeError('Unknown visual mutation; preserve menu owner for native teardown')
        if self.state in ('new', 'prepared'):
            if self.planner is not None:
                self.planner.close()
            self.state = 'restored'
            return
        if self.menu.panel is not self.panel or getattr(self.menu, '_presentation_owner', None) is not self:
            raise RuntimeError('Menu presentation ownership changed')
        if self.panel.state != 'closed':
            # A detached but reusable panel also needs its opacity restored.
            if self.panel.state not in ('open', 'built') or self.panel.uncertain:
                raise RuntimeError('Menu context is unavailable for visual restoration')
            if self.panel.state == 'open':
                self.menu._restore_presentation_frame()
            self.state = 'unknown'
            self.panel._mutate(self._invoke, self.restore_call)
        self.menu._presentation_suspended = False
        self.menu._presentation_owner = None
        self.planner.close()
        self.state = 'restored'

    close = restore
