"""Noninteractive, owned captions for portable story scenes."""
import math
from .widgets import OwnedMenuPanel
from .values import read_object_reference

def validate(document):
    rows=document.get('captions',[])
    if type(rows) is not list or len(rows)>64:raise ValueError('Up to 64 scene captions')
    previous=-1
    for row in rows:
        if type(row) is not dict or set(row)-{'phonemes','emotion','emotion_strength'}!={'at','end','speaker','text'}:raise ValueError('Invalid scene caption')
        if any(type(row[k]) not in (float,int) or not math.isfinite(row[k]) for k in ('at','end')) or not 0<=row['at']<row['end']<=document['duration'] or row['at']<previous:raise ValueError('Invalid caption time')
        for key,limit in (('speaker',40),('text',500)):
            if type(row[key]) is not str or not 1<=len(row[key])<=limit or any(ord(c)<32 and c!='\n' for c in row[key]):raise ValueError('Invalid caption text')
        previous=row['at']

class SceneCaptions(OwnedMenuPanel):
    BATCH_CONSTRUCTION=True
    def __init__(self,scope):
        super().__init__(scope,controls=1,cached_construction=True,selected_results=True)
        self.attached=False;self.last_text=None;self.last_controls=None;self.last_paused=None
    def build(self):
        super().build()
        backdrop=next(child for child in self.children if child.class_name=='Border')
        self._render_call(backdrop,'Border','SetBrushColor',InBrushColor={'R':0.,'G':0.,'B':0.,'A':0.})
        self.set_text(self.caption,'');return self
    def _build_contents(self):
        self.caption=self._spawn('CommonTextBlock')
        self._call(self.caption,'CommonTextBlock','SetStyle',InStyle=self._class('CTS_B1_SmallLine_Outline_C'))
        slot=self._place(self.caption,-700,-100,1400,90)
        self.title=self.detail=self.caption
        self.labels.append(self.caption)
        self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':.5,'Y':1.},'Maximum':{'X':.5,'Y':1.}})
        self._call(self.caption,'TextLayoutWidget','SetJustification',InJustification=1)
        self._call(self.caption,'Widget','SetVisibility',InVisibility=self.invisible)
        self.pause_backdrop=self._spawn('Border')
        pause_slot=self._place(self.pause_backdrop,-340,-110,680,220)
        self._call(pause_slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':.5,'Y':.5},'Maximum':{'X':.5,'Y':.5}})
        self._call(self.pause_backdrop,'Border','SetBrushColor',InBrushColor={'R':.015,'G':.012,'B':.01,'A':.88})
        self._call(self.pause_backdrop,'Widget','SetVisibility',InVisibility=self.collapsed)
        self.controls=self._spawn('CommonTextBlock')
        self.detail=self.controls
        self._call(self.controls,'CommonTextBlock','SetStyle',InStyle=self._class('CTS_B1_SmallLine_Outline_C'))
        self.controls_slot=self._place(self.controls,-550,32,1100,190)
        self._call(self.controls_slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':.5,'Y':0.},'Maximum':{'X':.5,'Y':0.}})
        self._call(self.controls,'TextLayoutWidget','SetJustification',InJustification=1)
        self._call(self.controls,'Widget','SetVisibility',InVisibility=self.invisible)
        self._call(self.widget,'Widget','SetVisibility',InVisibility=self.invisible)
    def show(self):
        self._render_call(self.widget,'UserWidget','AddToViewport',ZOrder=500)
        self.attached=True
    def update(self,rows,seconds,*,paused=False,skip_progress=0.):
        lines=[r['speaker']+': '+r['text'] for r in rows if r['at']<=seconds<r['end']]
        text='\n'.join(lines)
        if text!=self.last_text:self.set_text(self.caption,text);self.last_text=text
        if paused!=self.last_paused:
            self._render_call(self.pause_backdrop,'Widget','SetVisibility',InVisibility=self.invisible if paused else self.collapsed)
            self._render_call(self.controls_slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':.5,'Y':.5 if paused else 0.},'Maximum':{'X':.5,'Y':.5 if paused else 0.}})
            self._render_call(self.controls_slot,'CanvasPanelSlot','SetPosition',InPosition={'X':-550.,'Y':-85. if paused else 32.})
            self.last_paused=paused
        controls='CUTSCENE PAUSED\n\nE  Continue\nHold Esc for 3 seconds to skip' if paused else 'F Pause  |  Hold Esc 3 seconds to skip'
        if skip_progress:controls+='  '+str(round(skip_progress*100))+'%'
        if controls!=self.last_controls:self.set_text(self.controls,controls);self.last_controls=controls
    def close(self):
        if self.state=='closed':return True
        if self.attached:
            self._render_call(self.widget,'Widget','RemoveFromParent');self.attached=False
        return self.close_owned_tree()
