"""Experimental independently owned media widget using reflected SDK calls.

The caller owns its parent panel and must close this resource before removing
that panel. Abrupt-controller-disconnect playback cleanup is not yet validated;
do not advertise this as a released Cinematics playback capability.
"""
from ._scope import SessionScope
from .catalog import capture_matching, capture_selected
from .values import read_object_reference, read_values
from ._media_owner import NativeMediaOwner


class OwnedVideoWidget:
    def __init__(self, session):
        self.scope = SessionScope(session)
        self.planner = self.widget = self.source = self.player = None
        self.attached = False
        self.parent = None
        self.uncertain = False
        self.state = 'new'
        self.native_owner = None
        self._read_planner = None
        self._reads = {}

    @staticmethod
    def _one(rows):
        rows = tuple(rows)
        if len(rows) != 1:
            raise ValueError('Expected one media identity')
        return rows[0]

    def _class(self, name):
        return self._one(o for o in self.catalog.objects if o.name == name and o.class_name == 'Class')

    def _function(self, owner, name):
        index = self._class(owner).index
        return self._one(o for o in self.catalog.objects if o.name == name and o.outer_index == index)

    def _invoke(self, target, owner, name, **args):
        if self.uncertain or self.state == 'closed':
            raise RuntimeError('Media resource unavailable; uncertain calls cannot be retried')
        prepared = self.planner.prepare(target, self._function(owner, name), **args)
        self.uncertain = True
        result = prepared.invoke(refresh_from_result=True)
        self.uncertain = False
        return result

    def _call(self, target, owner, name, **args):
        with self._invoke(target, owner, name, **args) as result:
            return result.return_value

    def build(self, panel, path):
        if self.state != 'new' or not self.scope.supports_string_values:
            raise RuntimeError('A new resource and verified FString capability are required')
        if panel.state not in ('built', 'open') or panel.uncertain:
            raise RuntimeError('A known owned panel is required')
        if panel.scope.pid != self.scope.pid or panel.scope._session is not self.scope._session:
            raise RuntimeError('Media and panel must belong to the same controller session')
        self.parent = panel
        self.catalog = capture_matching(self.scope.pid, names=('CommonVideoPlayer','FileMediaSource',
            'MediaPlayer','GameplayStatics','Default__GameplayStatics','SpawnObject','SetFilePath',
            'SetVideo','Play','Pause','PlayFromStart','Close','IsReady','IsClosed','IsPlaying','IsPaused',
            'SetRate','Seek','Widget','SetVisibility','ESlateVisibility','SetZOrder','SetAnchors','Anchors','GetTime','GetDuration','Timespan','AddChildToCanvas','SetPosition','SetSize','RemoveFromParent','Vector2D'))
        self.catalog = self.catalog.with_observations(capture_selected(self.scope.pid,
            tuple((o.index,o.serial,o.address) for o in (panel.tree,panel.canvas))))
        self.planner = self.scope.invocation_planner(selected_results=True,catalog=self.catalog)
        default = self._one(o for o in self.catalog.objects if o.name == 'Default__GameplayStatics')
        def spawn(name):
            return self._invoke(default,'GameplayStatics','SpawnObject',
                ObjectClass=self._class(name),Outer=panel.tree).return_value
        self.state = 'building'
        self.widget = spawn('CommonVideoPlayer')
        self.source = spawn('FileMediaSource')
        for name in ('MediaPlayer','MediaTexture','SoundComponent'):
            ref, fresh = read_object_reference(self.planner._catalog,self.widget,
                                               self._class('CommonVideoPlayer'),name)
            if ref is None or ref.outer_index != self.widget.index:
                raise RuntimeError('Fresh widget did not create independent media children')
            self.planner.refresh_from(fresh)
            if name == 'MediaPlayer': self.player = ref
        self._call(self.source,'FileMediaSource','SetFilePath',Path=path)
        stored = read_values(self.planner._catalog,self.source)
        if stored.values.get((self._class('FileMediaSource').index,'FilePath')) != path:
            raise RuntimeError('Configured source path mismatch')
        self.state = 'configured'
        if getattr(self.scope._session._transport,'media_owner_protocol',0) == 1:
            close = self.planner.prepare(self.widget,self._function('CommonVideoPlayer','Close'))._plan
            remove = self.planner.prepare(self.widget,self._function('Widget','RemoveFromParent'))._plan
            lease = self._one(l for l in self.scope._leases if l.object == self.widget)
            self.native_owner = NativeMediaOwner(self.scope)
            self.native_owner.arm(lease,close,remove)
        return self

    def attach(self, panel, *, x=1100., y=220., width=700., height=394.):
        if self.state != 'configured' or self.attached or panel is not self.parent:
            raise RuntimeError('Expected a configured detached video')
        slot = self._invoke(panel.canvas,'CanvasPanel','AddChildToCanvas',Content=self.widget).return_value
        self.attached = True
        self._call(slot,'CanvasPanelSlot','SetPosition',InPosition={'X':float(x),'Y':float(y)})
        self._call(slot,'CanvasPanelSlot','SetSize',InSize={'X':float(width),'Y':float(height)})

    def attach_fullscreen(self, panel):
        """Stretch the owned media surface to its existing canvas; no resolution guess."""
        if self.state != 'configured' or self.attached or panel is not self.parent:
            raise RuntimeError('Expected a configured detached video')
        slot = self._invoke(panel.canvas,'CanvasPanel','AddChildToCanvas',Content=self.widget).return_value
        self.attached = True
        self._call(slot,'CanvasPanelSlot','SetPosition',InPosition={'X':0.,'Y':0.})
        self._call(slot,'CanvasPanelSlot','SetSize',InSize={'X':0.,'Y':0.})
        self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':0.,'Y':0.},'Maximum':{'X':1.,'Y':1.}})
        return slot

    def media_time(self):
        """Two bounded typed native getters; invalid/sentinel times are not clocks."""
        from ._pod_values import TimespanValue
        transport=self.scope._session._transport
        if type(getattr(transport,'timespan_values_protocol',0)) is not int or transport.timespan_values_protocol != 1:
            raise RuntimeError('Verified media Timespan return support is required')
        if self.player is None or self.state != 'opened' or self.uncertain:
            raise RuntimeError('A known opened owned media player is required')
        values={name:self._read(name) for name in ('GetTime','GetDuration')}
        if any(not isinstance(value,TimespanValue) or value.ticks<0 or value.ticks==0x7fffffffffffffff for value in values.values()):
            raise ValueError('Media timing is unknown or invalid')
        return dict(time_ticks=values['GetTime'].ticks,duration_ticks=values['GetDuration'].ticks,
                    time_seconds=values['GetTime'].seconds,duration_seconds=values['GetDuration'].seconds)

    def prepare_reads(self):
        """Observe exact getter schemas before playback, retaining native validation."""
        if self._read_planner is not None:return
        planner=self.scope.invocation_planner(selected_results=True,observations=self.planner.observations())
        names=['IsReady','IsPlaying','IsPaused','IsClosed']
        if getattr(self.scope._session._transport,'timespan_values_protocol',0)==1:
            names+=['GetTime','GetDuration']
        try:reads={name:planner.prepare(self.player,self._function('MediaPlayer',name)) for name in names}
        except BaseException:
            planner.close();raise
        self._read_planner=planner;self._reads=reads

    def _read(self,name):
        if self.uncertain or self.state=='closed':raise RuntimeError('Media resource unavailable')
        self.prepare_reads()
        with self._reads[name].invoke() as result:return result.return_value

    def media_position(self):
        from ._pod_values import TimespanValue
        if self.state!='opened':raise RuntimeError('Opened media required')
        value=self._read('GetTime')
        if not isinstance(value,TimespanValue) or value.ticks<0 or value.ticks==0x7fffffffffffffff:
            raise ValueError('Invalid copied media clock')
        return dict(time_ticks=value.ticks,time_seconds=value.seconds)

    def playback_status(self,*,opening=False):
        names=('IsReady','IsPlaying','IsPaused') if opening else ('IsPlaying','IsPaused')
        return dict(state=self.state,**{name:self._read(name) for name in names})

    def play(self):
        if self.state != 'configured' or not self.attached:
            raise RuntimeError('Expected a configured attached player')
        if self.native_owner is not None and self.native_owner.status() != 'armed':
            raise RuntimeError('Native media ownership was revoked')
        self.prepare_reads()
        self._call(self.widget,'CommonVideoPlayer','SetVideo',NewVideo=self.source)
        self.state = 'opened'

    def status(self):
        if self.player is None: return {'state':self.state}
        return dict(state=self.state, **{name:self._read(name)
            for name in ('IsReady','IsPlaying','IsPaused','IsClosed')})

    def pause(self):
        return self._call(self.player,'MediaPlayer','Pause')

    def resume(self):
        return self._call(self.player,'MediaPlayer','Play')

    def seek(self, seconds):
        """Seek an opened owned player using a copied finite Timespan value."""
        import math
        from ._pod_values import TimespanValue
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not 0<=seconds<=86400:
            raise ValueError('Media seek requires finite seconds between zero and one day')
        transport=self.scope._session._transport
        if type(getattr(transport,'timespan_values_protocol',0)) is not int or transport.timespan_values_protocol!=1:
            raise RuntimeError('Verified media Timespan input support is required')
        cap=getattr(transport,'media_seek_protocol',0)
        if type(cap) is not int or cap!=1:raise RuntimeError('Verified media Seek support is required')
        if self.state!='opened' or self.uncertain:raise RuntimeError('Known opened media required for seeking')
        return self._call(self.player,'MediaPlayer','Seek',Time=TimespanValue(round(seconds*10_000_000)))

    def restart(self):
        self._call(self.widget,'CommonVideoPlayer','PlayFromStart')

    def set_rate(self, rate):
        if type(rate) not in (int,float) or not .25 <= rate <= 2:
            raise ValueError('Playback rate must be between .25 and 2')
        return self._call(self.player,'MediaPlayer','SetRate',Rate=float(rate))

    def close(self):
        if self.state == 'closed': return
        if getattr(getattr(self,'native_owner',None),'_retiring',False) is True:
            if not self.retire_world():raise RuntimeError('Native media retirement deferred; preserve owner')
            return
        if self.uncertain:
            raise RuntimeError('Unknown media dispatch; preserve resources for session recovery')
        owner = getattr(self,'native_owner',None)
        if owner is not None:
            if not owner.close(): raise RuntimeError('Native media closure deferred; preserve owner')
            self.attached = False
        elif self.widget is not None and self.player is not None:
            self._call(self.widget,'CommonVideoPlayer','Close')
            if self.state == 'opened' and not self._call(self.player,'MediaPlayer','IsClosed'):
                raise RuntimeError('Media closure unconfirmed; preserve owner')
        if self.attached:
            self._call(self.widget,'Widget','RemoveFromParent')
            self.attached = False
        if self.planner is not None: self.planner.close()
        if self._read_planner is not None:self._read_planner.close()
        self.scope.close()
        self.state = 'closed'
        self.parent = None

    def retire_world(self):
        """Release old owned media holds without calling the old widget."""
        if self.state=='closed':return True
        if self.uncertain:raise RuntimeError('Unknown media mutation cannot be retired')
        if self.native_owner is None:
            raise RuntimeError('Native media ownership is required for retirement')
        if not self.native_owner.retire_world():return False
        self.attached=False
        if self.planner is not None:self.planner.close()
        if self._read_planner is not None:self._read_planner.close()
        from ._retired_tracking import close_lease_only_scope
        if not close_lease_only_scope(self.scope):return False
        self.state='closed';self.parent=None
        return True
