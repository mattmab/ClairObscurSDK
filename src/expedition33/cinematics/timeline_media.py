"""Owned movie surface synchronized to an authored sequence's frame clock."""
import math,time
from ..media import OwnedVideoWidget


class TimelineMedia:
    def __init__(self,scope,panel,path,rate,start,end=None,*,origin=None):
        if len(rate)!=2 or any(type(v) is not int or v<=0 for v in rate):raise ValueError('Positive native timeline rate required')
        if type(start) not in (int,float) or not math.isfinite(start):raise ValueError('Finite timeline start required')
        if end is not None and (type(end) not in (int,float) or not math.isfinite(end) or end<=start):
            raise ValueError('Movie end must follow its finite start')
        origin=start if origin is None else origin
        if type(origin) not in (int,float) or not math.isfinite(origin) or origin>start:
            raise ValueError('Finite movie clock origin must not follow its visible start')
        self.video=OwnedVideoWidget(scope);self.panel=panel;self.path=path
        self.rate=tuple(rate);self.start=start;self.end=end;self.origin=origin;self.ready=False;self.playing=False
        self.duration=None;self.last=None;self.deadline=None;self.shown=False
    def prepare(self):
        self.video.build(self.panel,self.path)
        slot=self.video.attach_fullscreen(self.panel)
        # The film is display-only and stays behind the existing timeline UI.
        self.video._call(slot,'CanvasPanelSlot','SetZOrder',InZOrder=-1)
        # Keep other scene content visible while the movie is opening and
        # before its authored start.  HitTestInvisible still renders a widget;
        # it is not a hidden state.
        self.video._call(self.video.widget,'Widget','SetVisibility',InVisibility=self.panel.collapsed)
        self.video.play();self.deadline=time.monotonic()+15.
    def sync(self,frame,playing):
        if type(frame) not in (int,float) or not math.isfinite(frame) or type(playing) is not bool:
            raise ValueError('Finite timeline position and Boolean playback state required')
        if self.deadline is None:raise RuntimeError('Prepare timeline media before synchronization')
        if not self.ready:
            status=self.video.playback_status(opening=True)
            if status.get('IsReady') is not True:
                if time.monotonic()>=self.deadline:raise ValueError('The authored movie did not become ready')
                return False
            timing=self.video.media_time();duration=timing['duration_seconds']
            if type(duration) not in (int,float) or not math.isfinite(duration) or duration<=0:
                raise ValueError('The authored movie has no finite duration')
            self.duration=duration;self.playing=status.get('IsPlaying') is True;self.ready=True
        seconds=max(0.,(frame-self.origin)*self.rate[1]/self.rate[0])
        visible=frame>=self.start and (self.end is None or frame<self.end) and seconds<self.duration
        active=playing and visible
        target=min(seconds,max(0.,self.duration-1e-6));key=(target,active,visible)
        if key==self.last:return True
        if self.playing and not active:
            if self.video.pause() is not True:raise ValueError('The authored movie did not pause')
            self.playing=False
        seek=self.last is None or not active or self.last[1]!=active
        if not seek:
            seek=abs(self.video.media_position()['time_seconds']-target)>.4
        if seek and self.video.seek(target) is not True:raise ValueError('The authored movie rejected timeline seeking')
        if active and not self.playing:
            if self.video.resume() is not True:raise ValueError('The authored movie did not start')
            self.playing=True
        if visible!=self.shown:
            self.video._call(self.video.widget,'Widget','SetVisibility',
                InVisibility=self.panel.invisible if visible else self.panel.collapsed)
            self.shown=visible
        self.last=key;return True
    def close(self):
        try:self.video.close()
        except RuntimeError as error:
            if str(error)=='Native media closure deferred; preserve owner':return False
            raise
        self.ready=False
        return self.video.state=='closed'
    def retire_world(self):
        if not self.video.retire_world():return False
        self.ready=False;return True
