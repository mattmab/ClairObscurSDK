"""Hide only pre-existing menu children; sibling media and input owner stay visible."""
import math
from expedition33.catalog import capture_matching,capture_selected
from expedition33.values import read_values
from .presentation import MenuPresentation

class MenuChildrenPresentation(MenuPresentation):
    def __init__(self,menu,stop_playback):
        super().__init__(menu)
        if not callable(stop_playback):raise TypeError('Playback stop callback required')
        self.stop_playback=stop_playback

    def prepare(self):
        if self.state != 'new' or self.panel.state != 'open' or self.panel.uncertain:
            raise RuntimeError('Prepare visual suspension only for a known open owned menu')
        if self.menu.panel is not self.panel or getattr(self.menu, '_presentation_owner', None) is not None:
            raise RuntimeError('Menu presentation is already owned or changed')
        scope = self.panel.scope
        scope._check()
        catalog = capture_matching(scope.pid, names=('Widget', 'SetRenderOpacity'))
        widgets=tuple(self.panel.children)
        if not widgets or len(widgets)>64 or self.panel.widget in widgets or self.panel.canvas in widgets:
            raise RuntimeError('Bounded owned menu children required')
        if len({(o.index,o.serial,o.address) for o in widgets}) != len(widgets):
            raise RuntimeError('Duplicate menu child identity')
        catalog = catalog.with_observations(capture_selected(scope.pid, tuple((widget.index,widget.serial,widget.address) for widget in widgets)))
        owner = catalog.by_index[catalog.find_class('Widget').index]
        functions = [o for o in catalog.objects if o.outer_index == owner.index and o.name == 'SetRenderOpacity' and o.class_name == 'Function']
        if len(functions) != 1:
            raise RuntimeError('Verified render-opacity setter is unavailable')
        self.planner = scope.invocation_planner(catalog=catalog, selected_results=True)
        hides=[];restores=[];opacities=[]
        for widget in widgets:
            values=read_values(catalog,widget);key=(owner.index,'RenderOpacity');opacity=values.values.get(key)
            if (values.types.get(key)!='FloatProperty' or key in values.errors or key in values.truncated or
                    type(opacity) is not float or not math.isfinite(opacity) or not 0.<=opacity<=1.):
                raise RuntimeError('Owned child render opacity is not verified')
            hides.append(self.planner.prepare(widget,functions[0],InOpacity=0.))
            restores.append(self.planner.prepare(widget,functions[0],InOpacity=opacity));opacities.append(opacity)
        self.hide_call,self.restore_call=tuple(hides),tuple(restores)
        self.original_opacity=tuple(opacities)
        self.state = 'prepared'
        return self

    @staticmethod
    def _invoke(calls):
        for call in calls:
            with call.invoke():pass

class FullscreenOverlayPresentation:
    """Gate menu callbacks behind an owned opaque overlay, without child I/O.

    The fullscreen owner creates backdrop, video and Stop above existing menu
    children. It alone acknowledges their closure before revealing the menu.
    """
    def __init__(self,menu,stop_playback):
        if not callable(stop_playback):raise TypeError('Playback stop callback required')
        self.menu,self.panel=menu,menu.panel
        self.stop_playback=stop_playback
        self.state='new';self.planner=None;self._overlay_closed=False

    def _context(self):
        if self.menu.panel is not self.panel or self.panel.state!='open' or self.panel.uncertain:
            raise RuntimeError('Fullscreen presentation context changed')

    def prepare(self):
        if self.state!='new':raise RuntimeError('Fullscreen presentation already prepared')
        self._context()
        if getattr(self.menu,'_presentation_owner',None) is not None:
            raise RuntimeError('Menu presentation already has an owner')
        self.state='prepared'
        return self

    def suspend(self):
        if self.state!='prepared':raise RuntimeError('Fullscreen presentation is not prepared')
        self._context()
        if getattr(self.menu,'_presentation_owner',None) is not None:
            raise RuntimeError('Menu presentation already has an owner')
        self.menu._presentation_owner=self
        self.menu._presentation_suspended=True
        self.state='suspended'

    def acknowledge_overlay_closed(self):
        self._overlay_closed=True

    def restore(self):
        if self.state=='restored':return
        if not self._overlay_closed:
            raise RuntimeError('Fullscreen overlay cleanup is not acknowledged')
        if self.menu.panel is not self.panel:
            raise RuntimeError('Fullscreen presentation panel changed')
        if self.state=='suspended':
            if getattr(self.menu,'_presentation_owner',None) is not self:
                raise RuntimeError('Fullscreen presentation owner changed')
            self._context()
            # Existing paint machinery decides whether a dirty frame needs work.
            # Leave callbacks gated until the current frame is restored.
            self.menu._restore_presentation_frame()
            self.menu._presentation_owner=None
            self.menu._presentation_suspended=False
        self.state='restored'

    close=restore
