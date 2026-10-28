"""Fullscreen media in the existing owned menu, with a durable visible Stop control."""
from expedition33.media import OwnedVideoWidget
from expedition33.catalog import capture_matching
from .media_presentation import FullscreenOverlayPresentation

class FullscreenMedia:
    def __init__(self,session):
        self.video=OwnedVideoWidget(session)
        self.presentation=None
        self.menu=self.button=self.label_frame=self.action=self.backdrop=None
        self.state='new'
        self._removed=set()
        self._control_uncertain=False
        self.audio_dependency=None

    def build(self,menu,path,stop_callback):
        if self.state!='new':raise RuntimeError('Fullscreen owner already used')
        self.menu=menu
        self.presentation=FullscreenOverlayPresentation(menu,stop_callback)
        self.video.build(menu.panel,path)
        self._build_stop(stop_callback)
        self.presentation.prepare()
        self.state='prepared'
        return self

    def _build_stop(self,callback):
        v=self.video;p=self.menu.panel
        extra=capture_matching(v.scope.pid,names=('Border','SetBrushColor','Button','CommonTextBlock','TextBlock','TextLayoutWidget','Overlay','OverlaySlot',
            'SetBackgroundColor','LinearColor','SetStyle','CTS_B1_SmallLine_Outline_C','SetText','SetJustification',
            'SetVisibility','ESlateVisibility','ETextJustify','EHorizontalAlignment','EVerticalAlignment',
            'AddChildToOverlay','SetHorizontalAlignment','SetVerticalAlignment','SetZOrder'))
        v.planner.refresh_from(v.planner._catalog.with_observations(extra));v.catalog=v.planner._catalog
        default=v._one(o for o in v.catalog.objects if o.name=='Default__GameplayStatics')
        def spawn(name):return v._invoke(default,'GameplayStatics','SpawnObject',ObjectClass=v._class(name),Outer=p.tree).return_value
        def place(widget,z_order):
            slot=v._invoke(p.canvas,'CanvasPanel','AddChildToCanvas',Content=widget).return_value
            v._call(slot,'CanvasPanelSlot','SetZOrder',InZOrder=z_order)
            v._call(slot,'CanvasPanelSlot','SetPosition',InPosition={'X':-390.,'Y':-100.})
            v._call(slot,'CanvasPanelSlot','SetSize',InSize={'X':360.,'Y':64.})
            v._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':1.,'Y':1.},'Maximum':{'X':1.,'Y':1.}})
        self.backdrop=spawn('Border')
        background_slot=v._invoke(p.canvas,'CanvasPanel','AddChildToCanvas',Content=self.backdrop).return_value
        v._call(background_slot,'CanvasPanelSlot','SetZOrder',InZOrder=10000)
        v._call(background_slot,'CanvasPanelSlot','SetPosition',InPosition={'X':0.,'Y':0.})
        v._call(background_slot,'CanvasPanelSlot','SetSize',InSize={'X':0.,'Y':0.})
        v._call(background_slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':0.,'Y':0.},'Maximum':{'X':1.,'Y':1.}})
        v._call(self.backdrop,'Border','SetBrushColor',InBrushColor={'R':0.,'G':0.,'B':0.,'A':1.})
        video_slot=v.attach_fullscreen(p)
        v._call(video_slot,'CanvasPanelSlot','SetZOrder',InZOrder=10001)
        self.button=spawn('Button');place(self.button,10002)
        v._call(self.button,'Button','SetBackgroundColor',InBackgroundColor={'R':.02,'G':.02,'B':.02,'A':.95})
        self.label_frame=spawn('Overlay');place(self.label_frame,10003)
        label=spawn('CommonTextBlock')
        style=v._one(o for o in v.catalog.objects if o.name=='CTS_B1_SmallLine_Outline_C')
        v._call(label,'CommonTextBlock','SetStyle',InStyle=style)
        v._call(label,'TextBlock','SetText',InText='Stop playback  [Esc]')
        v._call(label,'TextLayoutWidget','SetJustification',InJustification=1)
        slot=v._invoke(self.label_frame,'Overlay','AddChildToOverlay',Content=label).return_value
        v._call(slot,'OverlaySlot','SetHorizontalAlignment',InHorizontalAlignment=2)
        v._call(slot,'OverlaySlot','SetVerticalAlignment',InVerticalAlignment=2)
        v._call(self.label_frame,'Widget','SetVisibility',InVisibility=p.invisible)
        def stop(_event):
            if self.menu.panel is not p or p.state!='open':raise RuntimeError('Fullscreen context changed')
            return callback()
        self._control_uncertain=True
        self.action=p.menu.bind_control(self.button,stop)
        self._control_uncertain=False

    def play(self):
        if self.state!='prepared':raise RuntimeError('Fullscreen playback not prepared')
        if self.audio_dependency is not None:self.audio_dependency.start()
        self.presentation.suspend()
        self.video.play()
        self.state='opened'

    def resume(self):return self.video.resume()
    def media_time(self):return self.video.media_time()
    def media_position(self):return self.video.media_position()
    def playback_status(self,*,opening=False):return self.video.playback_status(opening=opening)
    def status(self):
        if self.state=='cleanup_pending':return dict(state=self.state,IsReady=False,IsPlaying=False,IsPaused=False)
        return self.video.status()

    def close(self):
        if self.state=='closed':return True
        self.state='cleanup_pending'
        # Keep visible Stop and all input/menu ownership while media close defers.
        if self._control_uncertain:raise RuntimeError('Stop registration outcome unknown; preserve native menu ownership')
        if self.video.uncertain:raise RuntimeError('Unknown media mutation; preserve fullscreen ownership')
        owner=getattr(self.video,'native_owner',None)
        if owner is not None and not owner.close():return False
        if self.audio_dependency is not None and not self.audio_dependency.close():return False
        if self.action is not None:
            if not self.action.remove():return False
            self.action=None
        for name in ('label_frame','button','backdrop'):
            widget=getattr(self,name)
            if widget is not None and name not in self._removed:
                self.video._call(widget,'Widget','RemoveFromParent')
                self._removed.add(name)
        self.video.close()
        if self.presentation is not None:
            if isinstance(self.presentation,FullscreenOverlayPresentation):
                self.presentation.acknowledge_overlay_closed()
            self.presentation.restore()
        self.state='closed'
        return True

    def retire_world(self):
        if self.state=='closed':return True
        self.state='retirement_pending'
        if self._control_uncertain or self.video.uncertain:
            raise RuntimeError('Unknown fullscreen ownership cannot be retired as complete')
        # Native media retirement proves the old epoch, revokes this old menu's
        # callbacks, retires audio, and releases the owned media collector. It
        # never calls CommonVideoPlayer.Close or an old Widget.RemoveFromParent.
        if not self.video.retire_world():return False
        retired=self.menu.panel.retire_world()
        if retired=='pending':return False
        if retired!='ack':raise RuntimeError('Fullscreen panel retirement is unknown')
        if self.audio_dependency is not None and not self.audio_dependency.retire_world():return False
        from .retirement import retire_presentation
        retire_presentation(self.presentation)
        self.action=self.button=self.label_frame=self.backdrop=None
        self.state='closed'
        return True
