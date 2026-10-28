"""Compact native timeline. Mouse drag seeking is owned by the scene game thread."""
from contextlib import nullcontext
from dataclasses import replace
from expedition33.widgets import OwnedMenuPanel
from expedition33.management_native import NativeManagementMenu
from expedition33.management_view import MenuFrame,MenuControl
from expedition33.management import ManagementError

from .palette import CLIPS,ANIMATIONS,animation_choices,animation_sets,actor_animation_owner
import textwrap

FPS=30

def visible_sequence_rows(rows,limit,selected=None):
    """Share bounded marker slots across lanes, retaining the selected track."""
    lanes={}
    for row in rows:lanes.setdefault(row['lane'],[]).append(row)
    chosen=[]
    for lane in lanes.values():
        match=next((i for i,row in enumerate(lane) if row['key']==selected),None)
        if match is not None:lane.insert(0,lane.pop(match))
    while lanes and len(chosen)<limit:
        for key in tuple(lanes):
            if len(chosen)>=limit:break
            chosen.append(lanes[key].pop(0))
            if not lanes[key]:del lanes[key]
    return chosen


def clip_name(event):
    if event['type']=='camera':return event['label']
    if event['type']=='animation':return ANIMATIONS.get(event['params']['asset'],{}).get('label','Bind pose')
    asset=event['params']['asset']
    return 'Whoosh' if asset=='sound' else asset.rsplit('.',1)[-1].replace('_',' ')

def selected_event(model):
    r=model.runtime;d=model.document;value=r.last.get('selected_clip',-1)
    key=None
    if 100<=value<200:
        index=value-100
        if index<len(d['actors']):key='anim-'+d['actors'][index]['id']
        else:
            events=[e for e in d['events'] if e['id'].startswith('useranim-')]
            slots=getattr(r,'animation_slots',{}) or {e['id']:i for i,e in enumerate(events)}
            key=next((key for key,slot in slots.items() if slot==index-6),None)
    elif 200<=value<232:
        index=value-200
        if index<9:key='audio-'+str(index)
        else:
            events=[e for e in d['events'] if e['id'].startswith('useraudio-')]
            slots=getattr(r,'audio_event_slots',{}) or {e['id']:i for i,e in enumerate(events)}
            key=next((key for key,slot in slots.items() if slot==index-9),None)
    return next((e for e in d['events'] if e['id']==key),None)

class TimelineView:
    def __init__(self,registry,model):
        self.registry=registry;self.model=model;self.closed=False;self.revision=0;self.picker=False;self.page=0;self.choices=();self.query='';self.selected_sound=None;self.audio_category='music';self.animation_group='character';self.animation_query='';self.selected_animation=None
    def matches(self):
        key=(id(self.model.audio_paths),self.query,self.audio_category)
        if getattr(self,'match_key',None)!=key:
            words=self.query.casefold().split()
            kinds=getattr(getattr(self.model.runtime,'registry',None),'audio_kinds',{})
            def category(path):
                kind=kinds.get(path,2)
                if self.audio_category=='music':return kind>=3 and any(x in path.lower() for x in ('/music','melod','mus_track'))
                if self.audio_category=='cues':return kind>=3
                return self.audio_category=='all' or kind==2
            self.match_rows=tuple(path for path in (self.model.audio_paths or ()) if category(path) and all(word in path.casefold() for word in words));self.match_key=key
        return self.match_rows
    def animation_context(self):
        actors=self.model.document['actors'];slot=self.model.runtime.last.get('selected',0)
        if not 0<=slot<len(actors):return None,None
        role,skeleton=self.model.animation_context(actors[slot]['id'])
        if getattr(self,'animation_role',role)!=role:self.animation_group='character';self.animation_query='';self.selected_animation=None;self.page=0
        self.animation_role=role
        return role,skeleton
    def animation_matches(self):
        role,skeleton=self.animation_context()
        return animation_choices(role,skeleton,self.animation_group,self.animation_query) if role else ()
    def pool(self):
        if self.picker=='sequences':
            workspace=self.model.editor.workspace if getattr(self.model,'sequence_timeline',False) else self.model.authored
            return tuple(row for row in workspace.catalog if self.query.casefold() in (row['title']+' '+row['path']).casefold())
        return self.matches() if self.picker=='audio' else self.animation_matches()
    def render(self):
        if self.picker=='sequences':return self._render_sources()
        if getattr(self.model,'sequence_timeline',False):return self._render_sequence()
        self.revision+=1;m=self.model;active=m.runtime.authoring
        labels=['Cursor (Home)','Actor <','Actor >','Preview actor','Stop preview','Start','-1 frame','+1 frame','Play / pause','Save','Exit editor','Add camera key','Update camera','Delete camera','Add animation','Audio library']
        enabled=[active]*16;pages=1
        if self.picker:
            pool=self.pool()
            pages=max(1,(len(pool)+7)//8);self.page=min(self.page,pages-1);self.choices=pool[self.page*8:self.page*8+8]
            labels+=['Previous clips','Next clips','Close picker'];enabled+=[active]*3
            for i in range(8):
                choice=self.choices[i] if i<len(self.choices) else None
                label=(choice.rsplit('.',1)[-1].replace('_',' ') if self.picker=='audio' else ANIMATIONS[choice]['label']) if choice else ''
                if choice and self.picker=='audio':label={2:'[File] ',3:'[Cue] ',4:'[Set] '}.get(getattr(getattr(m.runtime,'registry',None),'audio_kinds',{}).get(choice,2),'')+label
                if self.picker=='audio' and len(label)>56:label=label[:53]+'...'
                if choice and choice==(self.selected_sound if self.picker=='audio' else self.selected_animation):label='> '+label
                labels.append(label);enabled.append(active and choice is not None)
            labels+=['Search','Clear search','Preview sound' if self.picker=='audio' else 'Preview actor','Stop sound' if self.picker=='audio' else 'Stop preview','Add selected']
            enabled+=[active,active,active and (self.selected_sound is not None if self.picker=='audio' else bool(m.document['actors'])),active,active and (self.selected_sound is not None if self.picker=='audio' else self.selected_animation is not None and bool(m.document['actors']))]
        else:
            self.choices=();labels+=['Photo controls' if getattr(m.runtime,'photo_mode',False) else 'Hide timeline','Photo mode active' if getattr(m.runtime,'photo_mode',False) else 'Photo mode','Game sequences'];enabled+=[active,active and not getattr(m.runtime,'photo_mode',False),active]
        labels+=['']*(32-len(labels));enabled+=[False]*(32-len(enabled))
        chosen=selected_event(m);audio=chosen is not None and chosen['type']=='audio'
        labels+=['Music / melodies','Authored cues / sets','Sound files','All audio'] if self.picker=='audio' else ['Delete selected clip','Volume -5%','Volume +5%','Game music: '+('OFF' if m.document.get('mute_game_music',False) else 'ON')] if not self.picker else ['All compatible','Previous set','Next set','This character']
        enabled+=[active]*4 if self.picker=='audio' else [active and chosen is not None,active and audio,active and audio,active] if not self.picker else [active]*4
        controls=tuple(MenuControl(i,label,enabled[i]) for i,label in enumerate(labels))
        return MenuFrame(self.revision,'SCENE EDITOR | TIMELINE','',controls,self.page if self.picker else 0,pages,m.message,self.closed)
    def activate(self,revision,token,**kwargs):
        if self.picker=='sequences':return self._activate_sources(revision,token,**kwargs)
        if getattr(self.model,'sequence_timeline',False):return self._activate_sequence(revision,token,**kwargs)
        if revision!=self.revision or not 0<=token<36:raise ManagementError('Stale timeline control')
        m=self.model;r=m.runtime;slot=r.last.get('selected',0);count=len(m.document['actors'])
        if token==0:m.want_timeline=True
        elif token in (1,2) and count:r.editor_control(4,(slot+(-1 if token==1 else 1))%count)
        elif token in (3,4) and count:r.audition(slot,token==3)
        elif token==5:r.seek(0)
        elif token in (6,7):r.seek(max(0,min(m.document['duration'],(round(r.last.get('playhead',0)*FPS)+(-1 if token==6 else 1))/FPS)))
        elif token==8:r.editor_control(0 if r.last['state']=='timeline_playing' else 1)
        elif token==9:m.document=r.sync_document(m.document);m.save()
        elif token==10:m.want_stop=True
        elif token in (11,12,13):
            try:m.camera_key({11:'add',12:'update',13:'delete'}[token])
            except ValueError as error:m.message=str(error)
        elif token==14:self.picker='animation';self.page=0;self.animation_group='character';self.animation_query='';self.selected_animation=None
        elif token==15:
            self.picker='audio';self.page=0;self.audio_category='music'
            if m.audio_paths is None:m.want_audio_library=True;m.message='Loading game audio library...'
        elif token==16 and not self.picker:m.want_visibility=True
        elif token==17 and not self.picker:m.want_photo=True
        elif token in (16,17) and self.picker:
            n=len(self.pool())
            self.page=(self.page+(-1 if token==16 else 1))%max(1,(n+7)//8)
        elif token==18 and not self.picker:self.picker='sequences';self.page=0;self.query='';self.selected_source=None
        elif token==18:self.picker=False;m.pending_audio_preview=''
        elif 19<=token<=26 and self.picker and token-19<len(self.choices):
            if self.picker=='audio':self.selected_sound=self.choices[token-19];m.message=self.selected_sound
            else:self.selected_animation=self.choices[token-19];m.message='Selected '+ANIMATIONS[self.selected_animation]['label']+'. Add selected schedules it; Preview actor auditions the existing actor clip.'
        elif token==27 and self.picker:
            value=kwargs.get('value')
            if value is None:value=m.timeline.panel.read_field()
            if type(value) is not str or len(value)>160 or any(ord(c)<32 for c in value):raise ValueError('Search accepts up to 160 characters')

            if self.picker=='audio':self.query=value.strip()
            else:self.animation_query=value.strip()
            self.page=0
        elif token==28 and self.picker:
            if self.picker=='audio':self.query=''
            else:self.animation_query=''
            self.page=0
        elif token==29 and self.picker=='audio' and self.selected_sound:m.pending_audio_preview=self.selected_sound
        elif token==30 and self.picker=='audio':m.pending_audio_preview=''
        elif token==31 and self.picker=='audio' and self.selected_sound:
            try:m.queue_clip('audio',self.selected_sound)
            except ValueError as error:m.message=str(error)
        elif token in (29,30) and self.picker=='animation':r.audition(slot,token==29)
        elif token==31 and self.picker=='animation' and self.selected_animation:
            try:m.queue_clip('animation',self.selected_animation)
            except ValueError as error:m.message=str(error)
        elif 32<=token<=35 and self.picker=='animation':
            role,skeleton=self.animation_context();groups=list(animation_sets(role,skeleton)) if role else []
            if token==32:self.animation_group=None
            elif token==35:self.animation_group='character'
            elif groups:
                index=groups.index(self.animation_group) if self.animation_group in groups else (-1 if token==34 else 0)
                self.animation_group=groups[(index+(-1 if token==33 else 1))%len(groups)]
            self.selected_animation=None
            self.page=0
        elif 32<=token<=35 and self.picker=='audio':
            self.audio_category=('music','cues','files','all')[token-32];self.page=0
        elif 32<=token<=35 and not self.picker:
            event=selected_event(m)
            try:m.queue_timeline_edit({32:'delete',33:'quieter',34:'louder',35:'music'}[token],event['id'] if event else None)
            except ValueError as error:m.message=str(error)
        else:raise ManagementError('Unavailable timeline control')
        return self.render()
    def _render_sources(self):
        self.revision+=1;pool=self.pool();pages=max(1,(len(pool)+7)//8);self.page=min(self.page,pages-1)
        self.choices=pool[self.page*8:self.page*8+8]
        labels={16:'Previous sequences',17:'Next sequences',18:'Close library',27:'Search',28:'Clear search',31:'Load into timeline'}
        for i,row in enumerate(self.choices):labels[19+i]=('> ' if row['path']==getattr(self,'selected_source',None) else '')+row['title'][:54]
        controls=tuple(MenuControl(i,labels.get(i,''),i in labels and (i!=31 or bool(getattr(self,'selected_source',None)))) for i in range(36))
        return MenuFrame(self.revision,'SCENE EDITOR | TIMELINE','',controls,self.page,pages,'Game sequence library | Loading preserves the current custom scene and opens the selected sequence in this timeline.',self.closed)
    def _activate_sources(self,revision,token,**kwargs):
        if revision!=self.revision:raise ManagementError('Stale timeline control')
        if token==18:self.picker=False
        elif token in (16,17):self.page=(self.page+(-1 if token==16 else 1))%max(1,(len(self.pool())+7)//8)
        elif 19<=token<=26 and token-19<len(self.choices):self.selected_source=self.choices[token-19]['path']
        elif token==27:
            menu=self.model.menu if getattr(self.model,'sequence_timeline',False) else self.model.timeline
            value=kwargs['value'] if 'value' in kwargs else menu.panel.read_field()
            if type(value) is not str or len(value)>160 or any(ord(c)<32 for c in value):raise ValueError('Search accepts up to 160 characters')
            self.query=value.strip();self.page=0
        elif token==28:self.query='';self.page=0
        elif token==31 and getattr(self,'selected_source',None):
            owner=self.model.owner if getattr(self.model,'sequence_timeline',False) else self.model
            if owner is None:raise ManagementError('Source switching requires the Scene Editor workspace')
            owner.load_timeline_source(self.selected_source)
        else:raise ManagementError('Unavailable timeline control')
        return self.render()
    def _render_sequence(self):
        self.revision+=1;p=self.model
        labels={0:'Seek to frame',5:'Start playback',6:'-1 frame',7:'+1 frame',8:'Pause' if p.playing else 'Play',10:'Back to editor'}
        if getattr(p,'return_to_scene',False):labels[10]='Back to scene timeline'
        if not self.picker and getattr(p,'owner',None) is not None:labels[16]='Game sequences'
        editor=getattr(p,'editor',None);pages=1;disabled=set()
        if editor is not None:
            labels.update({9:'Save',14:'Track library',15:'Apply edits'})
            can_play=getattr(p,'playback_available',lambda:not getattr(p,'editing_only',False))()
            if getattr(p,'editing_only',False) and not can_play:
                labels[5]=labels[8]='Playback unavailable';disabled.update((5,8,15))
            if can_play:
                labels[1]='3D overview'
                if not self.picker:
                    labels.update({2:'Orbit left',3:'Orbit right',4:'Camera closer',11:'Camera farther',12:'Camera up',13:'Camera down'})
                    labels[17]='Exit flight view' if getattr(getattr(p,'flight',None),'active',False) else 'Flight editor'
                    labels[18]='Place whole scene here'
                    labels[19]='Hide timeline (Backspace)'
                    if getattr(p,'editing_only',False):disabled.add(19)
                    if not getattr(getattr(p,'flight',None),'active',False):disabled.add(18)
            from expedition33.cinematics.authored_copy import curve_edits_available
            transport=getattr(getattr(getattr(p,'scope',None),'_session',None),'_transport',None)
            if editor.document.get('key_edits') and not curve_edits_available(transport):
                labels[15]='Curve runtime required';disabled.add(15)
            if self.picker=='sequence':
                disabled.add(0)  # The shared field edits a property while the library is open.
                pool=editor.rows();pages=max(1,(len(pool)+7)//8);self.page=min(self.page,pages-1)
                self.choices=pool[self.page*8:self.page*8+8]
                labels.update({16:'Previous page',17:'Next page',18:'Close library',29:'Previous property',30:'Next property',
                    27:'Stage property',32:'Sections',33:'Cast',34:'Blueprint NPCs'})
                for token,category in ((32,'sections'),(33,'cast'),(34,'npc')):
                    if editor.category==category or (category=='sections' and editor.category=='keys'):labels[token]='[ '+labels[token]+' ]'
                if editor.category=='npc':
                    from expedition33.cinematics.blueprint_actor import available_profiles
                    profiles=available_profiles(transport)
                    labels.update({28:'Remove NPC',31:'Choose NPC Blueprint',35:'Add '+profiles[getattr(self,'npc_profile',0)%len(profiles)].title()})
                for i,(key,label) in enumerate(self.choices):labels[19+i]=('> ' if key==editor.selected else '')+'\n'.join(textwrap.wrap(label,48,break_long_words=True,break_on_hyphens=False)[:2])
                if editor.selected is None:disabled.update((27,29,30))
                if editor.category=='keys':labels[28]='Reset key'
                elif editor.category!='npc':labels.pop(28,None)
                if editor.category not in ('npc','keys') or editor.selected is None:disabled.add(28)
                field=editor.field()
                p.message=getattr(self,'sequence_error',None) or getattr(self,'sequence_notice',None) or ('Editing '+field[0]+' | Stage property, then Apply edits to preview' if field else 'Select an item on the left to inspect and edit it')
                warning=editor.cast_overlap_warning() if editor.category=='cast' else ''
                if warning:p.message+=' | '+warning
                labels[12]='Scene position';labels[13]='3D overview'
                if not can_play:disabled.add(13)
                if editor.category=='scene':p.message='Whole scene: position [X, Y, Z] in cm and yaw in degrees. Choose a property, stage it, then Apply edits. Save keeps placement.'
                if editor.category in ('sections','keys'):
                    labels[11]='Back to section' if editor.category=='keys' else 'Section keys'
                    if editor.category=='sections' and editor.selected is None:disabled.add(11)
                if editor.category=='keys':p.message+=' | Apply rebuilds a private sequence with these key edits.'
        controls=tuple(MenuControl(i,labels.get(i,''),bool(i in labels and i not in disabled and (p.ready or i==10))) for i in range(36))
        return MenuFrame(self.revision,'SCENE EDITOR | TIMELINE','',controls,self.page,pages,p.message,self.closed)
    def _activate_sequence(self,revision,token,**kwargs):
        if revision!=self.revision or type(token) is not int:raise ManagementError('Stale timeline control')
        p=self.model;editor=getattr(p,'editor',None)
        self.sequence_error=None
        if not p.ready and token!=10:raise ManagementError('Unavailable timeline control')
        actions={0:'seek',1:'overview',2:'orbit_left',3:'orbit_right',4:'closer',5:'start',6:'back',7:'forward',8:'toggle',9:'save',10:'close',15:'apply'}
        if not self.picker:actions.update({11:'farther',12:'up',13:'down',17:'flight',18:'place_view'})
        if token in actions:
            if token in (9,15):self.sequence_notice=self.sequence_error=None
            p.queue(actions[token])
        elif token==16 and not self.picker and getattr(p,'owner',None) is not None:
            self.picker='sequences';self.page=0;self.query='';self.selected_source=None
        elif editor is not None:
            if token==14:self.picker='sequence';self.page=0
            elif token==19 and not self.picker:p.queue('visibility')
            elif token==18:self.picker=False
            elif self.picker=='sequence':
                if token==12:
                    if editor.document.get('scene_position') is None and getattr(p,'scene_anchor',None) is not None:editor.workspace.place_scene(list(p.scene_anchor))
                    editor.category_changed('scene');editor.select('origin');self.page=0
                elif token==13:p.queue('overview')
                elif token==11:
                    try:
                        editor.back_to_section() if editor.category=='keys' else editor.open_keys()
                        self.page=0
                    except ValueError as error:self.sequence_error=str(error)
                elif token in (16,17):self.page=(self.page+(-1 if token==16 else 1))%max(1,(len(editor.rows())+7)//8)
                elif 19<=token<=26 and token-19<len(self.choices):
                    editor.select(self.choices[token-19][0]);self.sequence_notice=None
                elif token in (29,30):editor.move_property(-1 if token==29 else 1);self.sequence_notice=None
                elif token==27:
                    try:
                        editor.edit(kwargs['value'] if 'value' in kwargs else p.menu.panel.read_field())
                        self.sequence_notice='Property staged | Apply edits to update playback; Save to keep';self.sequence_error=None
                    except ValueError as error:self.sequence_error=str(error)
                elif token==28:
                    try:
                        editor.reset_key() if editor.category=='keys' else editor.remove_npc()
                        self.sequence_notice='Key reset to source' if editor.category=='keys' else 'NPC removed | Apply edits to update playback'
                    except ValueError as error:self.sequence_error=str(error)
                elif 32<=token<=34:
                    editor.category_changed(('sections','cast','npc')[token-32]);self.page=0;self.sequence_error=self.sequence_notice=None
                elif token==31:
                    from expedition33.cinematics.blueprint_actor import available_profiles
                    transport=getattr(getattr(getattr(p,'scope',None),'_session',None),'_transport',None)
                    profiles=available_profiles(transport);self.npc_profile=(getattr(self,'npc_profile',0)+1)%len(profiles)
                    self.sequence_notice='Next NPC: '+profiles[self.npc_profile].title()+' | Add creates a new track'
                elif token==35:
                    from expedition33.cinematics.blueprint_actor import available_profiles
                    transport=getattr(getattr(getattr(p,'scope',None),'_session',None),'_transport',None)
                    profiles=available_profiles(transport)
                    editor.add_npc(profiles[getattr(self,'npc_profile',0)%len(profiles)]);self.page=(len(editor.rows())-1)//8
                    self.sequence_notice='NPC track added | Edit its timing and placement, then Apply edits'
                else:raise ManagementError('Unavailable timeline control')
            else:raise ManagementError('Unavailable timeline control')
        else:raise ManagementError('Unavailable timeline control')
        return self.render()
    def close(self):self.closed=True

class TimelinePanel(OwnedMenuPanel):
    BATCH_CONSTRUCTION=True
    EXTRA_NAMES=('SetRenderScale','SetRenderTransformPivot','SetRenderOpacity','EditableText','GetText','Slider','GetValue','SetValue','SetStepSize')
    def __init__(self,session,**kwargs):
        super().__init__(session,controls=36,**kwargs);self.markers=[];self.clip_names=[];self.track_labels=[];self.placements={};self.rulers=[]
    def _place(self,child,*args):
        slot=super()._place(child,*args);self.placements[child.index]=slot;return slot
    def anchor(self,slot,x,y,x2=None,y2=None,render=False):
        (self._render_call if render else self._call)(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':x,'Y':y},'Maximum':{'X':x if x2 is None else x2,'Y':y if y2 is None else y2}})
    def box(self,x,y,w,h,color,x2=None,y2=None):
        border=self._spawn('Border');slot=self._place(border,0,0,w,h);self.anchor(slot,x,y,x2,y2)
        self._call(border,'Border','SetBrushColor',InBrushColor=dict(zip(('R','G','B','A'),color)))
        self._call(border,'Widget','SetVisibility',InVisibility=self.invisible)
        return border,slot
    def _build_contents(self):
        # Keep all timeline furniture in one independently visible layer.
        # Owned movie widgets attach to the outer canvas behind this layer.
        # Construction may flush inside _build_timeline_contents. Keep the
        # outer reference on the panel so that flush resolves a pending root.
        self.timeline_outer_canvas=self.canvas
        self.timeline_layer=self._spawn('CanvasPanel')
        slot=self._place(self.timeline_layer,0,0,0,0)
        self.anchor(slot,0.,0.,1.,1.)
        self.canvas=self.timeline_layer
        try:self._build_timeline_contents()
        finally:self.canvas=self.timeline_outer_canvas
    def _build_timeline_contents(self):
        # Reuse the native focus owner, but keep the world visible through its backdrop.
        self._call(self.children[0],'Border','SetBrushColor',InBrushColor={'R':0.,'G':0.,'B':0.,'A':0.})
        self.box(.015,.715,0,0,(.015,.02,.03,.92),.985,.995)
        self.library_back,self.library_back_slot=self.box(.015,.105,0,0,(.015,.02,.03,.97),.985,.715)
        self.library_panes=[self.box(.025,.19,0,0,(.025,.045,.065,.98),.385,.70)[0],self.box(.40,.19,0,0,(.035,.055,.075,.98),.975,.70)[0]]
        self.title=self._label(30,0,1500,40);self._anchor_label(self.title,.0,.81)
        self.detail=self._label(30,0,1700,40);self._anchor_label(self.detail,.0,.833)
        for y,name in ((.86,'ANIM'),(.885,'AUDIO'),(.91,'CAM')):
            label=self._label(2,0,140,30);self._anchor_label(label,0.,y);self.track_labels.append((label,name));self.labels.append(label)
            self.box(.08,y,0,2,(.4,.45,.5,1.),.92,y)
        # Buttons must remain the first entries in labels for NativeManagementMenu.
        extra=list(self.labels);self.labels=[]
        for i in range(self.count):
            if i>=32:x,y,width=.03+(i-32)*.24,.125,390
            elif i>=27:x,y,width=.03+(i-27)*.19,.55,310
            elif i>=19:x,y,width=.08+((i-19)%2)*.44,.27+((i-19)//2)*.072,740
            elif i>=14:x,y,width=.03+(i-14)*.19,.75,310
            elif i>=11:x,y,width=.08+(i-11)*.20,.78,310
            else:x,y,width=(.02+(i%6)*.16,.95 if i<6 else .975,250)
            button=self._spawn('Button');slot=self._place(button,0,0,width,24 if i<11 else 28);self.anchor(slot,x,y)
            self._call(button,'Button','SetBackgroundColor',InBackgroundColor={'R':.08,'G':.12,'B':.2,'A':.95});self.buttons.append(button)
            label=self._label(0,0,width,24 if i<11 else 28,centered=True)
            # centered labels are nested under their own Overlay, the last placed child.
            overlay=self.children[-1];label_slot=self.placements[overlay.index]
            self.anchor(label_slot,x,y);self.labels.append(label)
            if not hasattr(self,'control_slots'):self.control_slots=[]
            self.control_slots.append((slot,label_slot))
            self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':.5,'Y':.5})
            self._call(label,'Widget','SetRenderScale',Scale={'X':.72,'Y':.72})
            self._visible[i]=self._enabled[i]=True
            if i>=32:self.category_slots=getattr(self,'category_slots',[])+[(slot,label_slot)]
        self.labels.extend(extra)
        for _ in range(80):
            self.markers.append(self.box(.08,.86,14,16,(.2,.8,1.,1.)))
            label=self._label(20,-5,600,35);self._anchor_label(label,.08,.86)
            self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
            self._call(label,'Widget','SetRenderScale',Scale={'X':.42,'Y':.42});self.labels.append(label);self.clip_names.append(label)
        self.playhead,self.playhead_slot=self.box(.08,.855,3,0,(1.,.65,.05,1.),.08,.94)
        for i in range(5):
            label=self._label(-10,0,140,30);self._anchor_label(label,.08+.84*i/4,.931)
            self._call(label,'Widget','SetRenderScale',Scale={'X':.6,'Y':.6});self.labels.append(label);self.rulers.append(label)
        for label in (self.title,self.detail,*[item[0] for item in self.track_labels]):
            self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
            self._call(label,'Widget','SetRenderScale',Scale={'X':.68,'Y':.68})
        self.field_back,self.field_back_slot=self.box(.08,.20,1450,45,(.008,.012,.02,.98))
        self.field=self._spawn('EditableText');slot=self._place(self.field,8,0,1430,42);self.anchor(slot,.08,.20)
        self.field_value=None;self.last_draw=None
        self.inspector=self._label(0,0,1450,420);self._anchor_label(self.inspector,.415,.205)
        self.labels.append(self.inspector)
        self._call(self.inspector,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
        self._call(self.inspector,'Widget','SetRenderScale',Scale={'X':.65,'Y':.65})
        self._call(self.inspector,'Widget','SetVisibility',InVisibility=self.collapsed)
        self.library_status=self._label(0,0,1450,105);self._anchor_label(self.library_status,.415,.615)
        self.property_caption=self._label(0,0,1400,50);self._anchor_label(self.property_caption,.415,.455)
        for label in (self.library_status,self.property_caption):
            self.labels.append(label)
            self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
            self._call(label,'Widget','SetRenderScale',Scale={'X':.65,'Y':.65})
            self._call(label,'Widget','SetVisibility',InVisibility=self.collapsed)
        # Slate owns capture and drag tracking, just as it does for the Mods
        # text-size slider. This transparent surface covers all source lanes.
        self.scrubber=self._spawn('Slider');slot=self._place(self.scrubber,0,0,0,0)
        self.anchor(slot,.08,.85,.92,.94)
        self._flush_layout()  # Slider setters are outside the layout-batch whitelist.
        self._call(self.scrubber,'Widget','SetRenderOpacity',InOpacity=.01)
        self._call(self.scrubber,'Slider','SetStepSize',InValue=.000001)
        self._call(self.scrubber,'Widget','SetVisibility',InVisibility=self.collapsed)
        self.scrub_value=None
    def read_scrub(self):
        with self._planner.prepare(self.scrubber,self._function('Slider','GetValue')).invoke() as result:
            value=float(result.return_value)
        previous=self.scrub_value;self.scrub_value=value
        return value if previous is not None and abs(value-previous)>1e-6 else None
    def restore_child_focus(self):
        # Slate sliders own keyboard focus independently of button callbacks.
        # Hand it back before their tree is detached, as the Mods sliders do.
        if self.state!='open' or self.uncertain:return
        for child in (self.scrubber,self.field):
            with self._planner.prepare(child,self._function('Widget','HasKeyboardFocus')).invoke() as result:
                focused=bool(result.return_value)
            if focused:
                self._render_call(self.buttons[0],'Widget','SetUserFocus',PlayerController=self.player)
                return
    def position_scrub(self,value):
        # This transparent slider is an input surface. The separate playhead is
        # the output. After initial placement, only Slate may change its value:
        # even checking GetValue before SetValue leaves a race in which a drag
        # arrives between those calls and playback paint erases its endpoint.
        if self.scrub_value is not None:return
        queue,self._paint_queue=self._paint_queue,None
        try:self._render_call(self.scrubber,'Slider','SetValue',InValue=value)
        finally:self._paint_queue=queue
        self.scrub_value=value
    def set_field(self,value):
        if self.field_value==value:return
        queue,self._paint_queue=self._paint_queue,None
        try:self._render_call(self.field,'EditableText','SetText',InText=value)
        finally:self._paint_queue=queue
        self.field_value=value
    def read_field(self):
        with self._planner.prepare(self.field,self._function('EditableText','GetText')).invoke() as result:return str(result.return_value)
    def layout_sequence_field(self,library):
        if getattr(self,'_sequence_field_layout',None)==library:return
        x,y=(.415,.495) if library else (.72,.78)
        for widget,width in ((self.field,1000 if library else 200),(self.field_back,1020 if library else 220)):
            slot=self.placements[widget.index]
            self.anchor(slot,x,y,render=True)
            self._render_call(slot,'CanvasPanelSlot','SetSize',InSize={'X':width,'Y':42 if widget is self.field else 45})
        self._sequence_field_layout=library
    def layout_sequence_library(self,view):
        library=view.picker=='sequence'
        for label in (self.inspector,self.library_status,self.property_caption):
            self._render_call(label,'Widget','SetVisibility',InVisibility=self.invisible if library else self.collapsed)
        # Keep the ruler and transport visible below this workspace. The list
        # uses one column; editing and feedback have dedicated inspector space.
        # Two wrapped lines need the full row height at the supported text
        # scale; the former 52px box clipped the second line into its neighbour.
        layout={i:(.035,.215+(i-19)*.058,650,60) for i in range(19,27)}
        layout.update({27:(.415,.555,330,36),28:(.79,.555,330,36),
            29:(.415,.405,330,36),30:(.60,.405,330,36),31:(.60,.555,330,36),
            16:(.035,.68,310,28),17:(.21,.68,310,28),18:(.79,.745,330,30),
            14:(.035,.745,340,30),15:(.415,.745,330,30),
            11:(.21,.745,340,30),12:(.415,.785,330,28),13:(.60,.785,330,28)})
        signature=library
        if getattr(self,'_library_layout',None)!=signature:
            for i,(x,y,width,height) in layout.items():
                if not library:
                    if i>=27:x,y,width=.03+(i-27)*.19,.55,310
                    elif i>=19:x,y,width=.03,.68,310
                    elif i>=14:x,y,width=.03+(i-14)*.19,.75,310
                    else:x,y,width=.08+(i-11)*.20,.78,310
                    height=28
                for slot in self.control_slots[i]:
                    self.anchor(slot,x,y,render=True)
                    self._render_call(slot,'CanvasPanelSlot','SetSize',InSize={'X':width,'Y':height})
            self._library_layout=signature
        if not library:return
        editor=view.model.editor;rows=editor.rows()
        chosen=next((label for key,label in rows if key==editor.selected),None)
        def wrap(value,width=76):return '\n'.join(textwrap.wrap(str(value),width,break_long_words=True,break_on_hyphens=False))
        heading={'sections':'SECTIONS','keys':'SECTION KEYS','cast':'CAST REPLACEMENT','npc':'BLUEPRINT NPC','scene':'WHOLE SCENE POSITION'}[editor.category]
        lines=[heading+'  |  '+str(len(rows))+' items  |  Page '+str(view.page+1)+'/'+str(max(1,(len(rows)+7)//8)),wrap(chosen or 'Choose an item from the list'), '']
        properties=editor.properties()
        if chosen:
            start=max(0,min(editor.property_index-1,len(properties)-3))
            for index,(name,value) in enumerate(properties[start:start+3],start):
                lines.append(wrap(('EDITING  ' if index==editor.property_index else '  ')+name+': '+str(value)))
        else:
            lines.append({'cast':'Select a character to replace its profile. The original source stays unchanged.',
                'npc':'Add an NPC track, then set its timing, Blueprint profile and position.',
                'sections':'Select a section to adjust its range or inspect its channel keys.'}.get(editor.category,'Select an item to inspect its properties.'))
        self.set_text(self.inspector,'\n'.join(lines))
        field=editor.field()
        self.set_text(self.property_caption,('VALUE  |  '+field[0]+'  |  '+str(editor.property_index+1)+'/'+str(len(properties))) if field else 'VALUE  |  Select an item first')
        applied=editor.document==view.model.document and not getattr(view.model,'editing_only',False)
        state=('PREVIEW UP TO DATE' if applied else 'APPLY REQUIRED')+'  |  '+('UNSAVED' if editor.workspace.dirty else 'SAVED')
        self.set_text(self.library_status,state+'\n'+wrap(view.model.message))
        for token,category in ((32,'sections'),(33,'cast'),(34,'npc')):
            active=editor.category==category or (category=='sections' and editor.category=='keys')
            color=(.16,.34,.43,1.) if active else (.08,.12,.2,.95)
            self._render_call(self.buttons[token],'Button','SetBackgroundColor',InBackgroundColor=dict(zip(('R','G','B','A'),color)))
        for i in range(19,27):
            selected=i-19<len(view.choices) and view.choices[i-19][0]==editor.selected
            color=(.16,.34,.43,1.) if selected else (.055,.09,.13,1.)
            self._render_call(self.buttons[i],'Button','SetBackgroundColor',InBackgroundColor=dict(zip(('R','G','B','A'),color)))
    def _anchor_label(self,label,x,y):
        self.anchor(self.placements[label.index],x,y)
    def draw(self,model):
        if getattr(model,'sequence_timeline',False):return self._draw_sequence(model)
        r=model.runtime;d=model.document;t=r.last.get('playhead',0);slot=r.last.get('selected',0);name=d['actors'][slot]['name'] if slot<len(d['actors']) else 'None'
        cam=r.last.get('selected_camera',-1)
        selected=r.last.get('selected_clip',-1);chosen=selected_event(model)
        caption='Selected: '+clip_name(chosen) if chosen else 'Drag start markers; empty track to scrub'
        if chosen is not None and chosen['type']=='audio':caption+=f' | Volume {chosen["params"]["volume"]:.0%}'
        current_view=getattr(getattr(model,'timeline',None),'view',None)
        if current_view is not None and current_view.picker=='audio' and current_view.selected_sound:caption='Sound: '+current_view.selected_sound.rsplit('.',1)[-1]
        self.set_text(self.title,'SCENE EDITOR | '+d['name']+(' | UNSAVED' if model.dirty else '')+' | '+('PHOTO' if getattr(r,'photo_mode',False) else 'FLIGHT')+' | Backspace: timeline | Home: cursor')
        view=getattr(getattr(model,'timeline',None),'view',None)
        if view is not None and view.picker:
            if view.picker=='audio':self.set_text(self.title,f'AUDIO LIBRARY | {len(view.matches())} results | Page {view.page+1}/{max(1,(len(view.matches())+7)//8)} | Type above, then Search')
            elif view.picker=='sequences':
                self.set_text(self.title,f'GAME SEQUENCE LIBRARY | {len(view.pool())} results | Page {view.page+1}/{max(1,(len(view.pool())+7)//8)}')
                caption='Select a source, then Load into timeline. The current custom scene is preserved.'
            else:self.set_text(self.title,f'ANIMATION LIBRARY | {len(view.animation_matches())} results | {(actor_animation_owner(view.animation_context()[0]) if view.animation_group=="character" and view.animation_context()[0] else view.animation_group or "All compatible")} | Page {view.page+1}/{max(1,(len(view.animation_matches())+7)//8)}')
        if current_view is not None and current_view.picker=='animation':caption=('Selected: '+ANIMATIONS[current_view.selected_animation]['label'] if current_view.selected_animation else 'Character clips first; use Previous/Next set for shared or other character sets')
        self.set_text(self.detail,f'Frame {round(t*FPS)} / {round(d["duration"]*FPS)}  |  {t:.3f}s  |  {name}  |  {caption}')
        x=.08+.84*t/d['duration'];self.anchor(self.playhead_slot,x,.855,x,.94,render=True)
        signature=(slot,cam,selected,tuple((e['id'],e['type'],e['at'],e['params'].get('asset'),e['params'].get('volume')) for e in d['events']),tuple(('camera',k['at']) for k in d.get('camera_keys',[])))
        if signature==self.last_draw:return
        native=getattr(r,'author_plan',None)
        audio_slots={f'audio-{i}':i for i in range(9)};audio_slots.update({key:9+slot for key,slot in (getattr(r,'audio_event_slots',{}) or {e['id']:i for i,e in enumerate(e for e in d['events'] if e['id'].startswith('useraudio-'))}).items()})
        actor_id=d['actors'][slot]['id'] if slot<len(d['actors']) else None
        events=[e for e in d['events'] if e['type']=='animation' and e['target']==actor_id or e['type']=='audio' and (native is None or native[83+audio_slots[e['id']]]>=0)]+[dict(type='camera',at=k['at'],label=f'Camera {i+1}',selected=i==cam) for i,k in enumerate(d.get('camera_keys',[]))]
        for i,(marker,where) in enumerate(self.markers):
            self._render_call(marker,'Widget','SetVisibility',InVisibility=self.invisible if i<len(events) else self.collapsed)
            label=self.clip_names[i]
            self._render_call(label,'Widget','SetVisibility',InVisibility=self.invisible if i<len(events) else self.collapsed)
            if i<len(events):
                e=events[i];y={'animation':.86,'audio':.885,'camera':.91}[e['type']];x=.08+.84*e['at']/d['duration'];self.anchor(where,x,y,render=True)
                title=clip_name(e);title=title if len(title)<=24 else title[:21]+'...'
                self.set_text(label,title+' @ '+f'{e["at"]:.2f}s')
                self.anchor(self.placements[label.index],x,y,render=True)
                color=(1.,.65,.05,1.) if e.get('selected') or e is chosen else {'animation':(.2,.8,1.,1.),'audio':(.3,1.,.5,1.),'camera':(1.,.3,.85,1.)}[e['type']]
                self._render_call(marker,'Border','SetBrushColor',InBrushColor=dict(zip(('R','G','B','A'),color)))
        for label,name in self.track_labels:self.set_text(label,name)
        for i,label in enumerate(self.rulers):self.set_text(label,f'{round(d["duration"]*FPS*i/4)}f')
        self.last_draw=signature

    def _draw_sequence(self,model):
        # Game-authored players use their own native frame rate and origin.
        start,end=model.start_frame,model.end_frame;span=max(1,end-start)
        cursor=model.frame+model.subframe;x=.08+.84*max(0.,min(1.,(cursor-start)/span))
        self.position_scrub(max(0.,min(1.,(cursor-start)/span)))
        self.set_text(self.title,'SCENE EDITOR | '+model.profile.saved_id+' | '+('EDITED' if model.edited else 'SOURCE'))
        self.set_text(self.detail,model.detail())
        self.anchor(self.playhead_slot,x,.855,x,.94,render=True)
        document=model.document or {}
        source_rows,projection_error=self._sequence_projection(model,document)
        rows=[dict(r,lane=.885 if r['name']=='AudioSection' else .86,key=r['path'],instance=r['instance']) for r in source_rows]
        rows.extend(dict(r,lane=.91,key=r['id']) for r in document.get('npc_tracks',()))
        if projection_error:self.set_text(self.detail,model.detail()+' | Source ruler: '+projection_error)
        selected=getattr(getattr(model,'editor',None),'selected',None)
        signature=(start,end,selected,tuple((r['key'],r.get('instance'),r['name'],r['start'],r['end']) for r in rows))
        if signature==self.last_draw:return
        lane_counts={lane:sum(r['lane']==lane for r in rows) for lane in {r['lane'] for r in rows}}
        rows=visible_sequence_rows(rows,len(self.markers),selected)
        # Dense authored sections often share a start. Keep every marker, but
        # give each lane one readable caption, preferring the selected track.
        captions={}
        for i,row in enumerate(rows[:len(self.markers)]):
            if row['lane'] not in captions or row['key']==selected:captions[row['lane']]=i
        for i,(marker,where) in enumerate(self.markers):
            visible=i<len(rows)
            self._render_call(marker,'Widget','SetVisibility',InVisibility=self.invisible if visible else self.collapsed)
            caption=visible and captions.get(rows[i]['lane'])==i
            self._render_call(self.clip_names[i],'Widget','SetVisibility',InVisibility=self.invisible if caption else self.collapsed)
            if visible:
                row=rows[i];at=.08+.84*max(0.,min(1.,(row['start']-start)/span))
                self.anchor(where,at,row['lane'],render=True)
                if caption:
                    self.anchor(self.placements[self.clip_names[i].index],.08,row['lane'],render=True)
                    count=lane_counts[row['lane']]
                    extra=f' | +{count-1} tracks' if count>1 else ''
                    self.set_text(self.clip_names[i],f'{row["name"]} [{float(row["start"]):g}, {float(row["end"]):g})f'+extra)
        for label,name in zip(self.track_labels,('SOURCE','AUDIO','NPC')):self.set_text(label[0],name)
        for i,label in enumerate(self.rulers):self.set_text(label,f'{round(start+span*i/4)}f')
        self.last_draw=signature

    def _sequence_projection(self,model,document):
        """Reuse the applied snapshot's nested projection while the cursor moves.

        A preview owns its validated document and replaces it when edits are
        applied. Keep the object itself, rather than only its id, so a later
        allocation cannot accidentally match a stale cached projection. Other
        callers do not make the same immutability promise and must recompute.
        """
        rate=tuple(model.rate)
        cached=getattr(self,'_projection_cache',None)
        if (getattr(model,'projection_snapshot',False) is True and cached is not None
                and cached[0] is document and cached[1]==rate):
            return cached[2]
        from .sequence_projection import project_sections
        try:
            rows,issues=project_sections(document,rate)
            error=f'{len(issues)} shot mappings unavailable; see source properties' if issues else None
        except (ValueError,KeyError) as exc:rows=();error=str(exc)
        result=(rows,error)
        self._projection_cache=(document,rate,result) if getattr(model,'projection_snapshot',False) is True else None
        return result

class TimelineMenu(NativeManagementMenu):
    def set_sequence_shown(self,shown):
        panel=self.panel
        # Keep the input owner attached so Backspace can restore the overlay.
        # HitTestInvisible prevents invisible buttons/slider receiving clicks.
        panel._render_call(panel.canvas,'Widget','SetVisibility',InVisibility=panel.visible if shown else panel.invisible)
        if getattr(self.model,'media',None) is not None:
            panel._render_call(panel.timeline_layer,'Widget','SetRenderOpacity',InOpacity=1. if shown else 0.)
        else:
            panel._render_call(panel.canvas,'Widget','SetRenderOpacity',InOpacity=1. if shown else 0.)
        self.hidden=not shown
    def hide(self):
        self.panel.restore_child_focus()
        return super().hide()
    def poll_scrub(self):
        if not self._accept_input or self._presentation_suspended or self.panel.state!='open':return None
        return self.panel.read_scrub()
    def __init__(self,session,registry,model):
        self.model=model;self.passive=False;self.hidden=False;self.registered=False;self.mirror=None
        super().__init__(session,registry,cached_planning=True,cached_construction=True,selected_results=True,reusable=True,view_factory=lambda registry:TimelineView(registry,model),panel_factory=TimelinePanel)
    def prepare(self):
        if getattr(self.model,'sequence_timeline',False):return super().prepare()
        # Registering timeline shortcuts retains AddToViewport. Stabilize its
        # identity before either panel captures/caches native menu plans.
        from expedition33.catalog import capture_matching
        c=capture_matching(self.model.session.pid,names=('AddToViewport','UserWidget'))
        owner=c.find_class('UserWidget').index
        function=next(o for o in c.objects if o.class_name=='Function' and o.name=='AddToViewport' and o.outer_index==owner)
        self.viewport_function=self.model.runtime.scope.retain(function)
        result=super().prepare()
        # A display-only copy stays in the viewport during input-owner handoff.
        # It never acquires focus or binds callbacks.
        self.mirror=TimelinePanel(self.model.session,cached_construction=True,selected_results=True)
        self.mirror.build();self.mirror.enable_cached_planning()
        self.mirror._render_call(self.mirror.widget,'Widget','SetVisibility',InVisibility=self.mirror.invisible)
        self.mirror._render_call(self.mirror.widget,'Widget','SetRenderOpacity',InOpacity=0.)
        self.mirror._render_call(self.mirror.widget,'UserWidget','AddToViewport',ZOrder=9999)
        self._paint()
        return result
    def _open(self):
        if getattr(self.model,'sequence_timeline',False):return super()._open()
        if self.panel.state=='new':self.prepare()
        if not self.registered or getattr(self,'registered_scope',None) is not self.model.runtime.scope:
            self.model.runtime.timeline_owner(self.panel,False)
            self.registered=True;self.registered_scope=self.model.runtime.scope
            # Only a new native scene owner needs new registration observations.
            if self.panel.state=='built':
                from expedition33.catalog import capture_matching
                observed=capture_matching(self.model.session.pid,names=('AddToViewport',))
                current=self.panel._planner._catalog.with_observations(observed)
                self.panel.catalog=current
                self.panel._functions.pop(('UserWidget','AddToViewport'),None)
                self.panel._planner.refresh_from(current)
        return super()._open()
    def set_cursor(self,enabled):
        from expedition33._reader import ReadBatch,active_reader
        with ReadBatch(self.model.session.pid) if active_reader() is None else nullcontext():
            return self._set_cursor(enabled)
    def _set_cursor(self,enabled):
        if enabled:
            if self.passive:
                self.view.closed=False
                self.panel._render_call(self.panel.widget,'Widget','SetVisibility',InVisibility=self.panel.visible)
                self.open()
                if self.mirror is not None:self.mirror._render_call(self.mirror.widget,'Widget','SetRenderOpacity',InOpacity=0.)
                self.passive=False
        elif not self.passive:
            if self.mirror is not None:self.mirror._render_call(self.mirror.widget,'Widget','SetRenderOpacity',InOpacity=1.)
            if self.panel.state=='open':self.hide()
            self.view.closed=False;self.passive=True
    def set_shown(self, shown):
        if shown==self.hidden:
            if shown:
                self.mirror._render_call(self.mirror.widget,'UserWidget','AddToViewport',ZOrder=9999)
                self.mirror._render_call(self.mirror.widget,'Widget','SetRenderOpacity',InOpacity=1.)
            else:
                self.set_cursor(False)
                self.mirror._render_call(self.mirror.widget,'Widget','RemoveFromParent')
            self.hidden=not shown
    def draw_tracks(self):
        self.sync_sequence_flight_controls()
        for panel in (self.panel,self.mirror):
            if panel is not None:
                with panel.paint_batch():panel.draw(self.model)
    def sync_sequence_flight_controls(self):
        """Keep flight feedback current without replacing a captured slider."""
        if not getattr(self.model,'sequence_timeline',False) or self.view.picker:return
        active=bool(getattr(getattr(self.model,'flight',None),'active',False))
        controls=[];changed=False
        for control in self.frame.controls:
            updated=control
            if control.token==17:updated=replace(control,label='Exit flight view' if active else 'Flight editor')
            elif control.token==18:updated=replace(control,enabled=active)
            if updated!=control:
                self.panel.set_text(self.panel.labels[control.token],updated.label)
                self.panel.set_enabled(control.token,updated.enabled)
                changed=True
            controls.append(updated)
        if changed:self.frame=replace(self.frame,controls=tuple(controls))
    def close(self):
        if getattr(self.model,'sequence_timeline',False):
            self.panel.restore_child_focus()
            return super().close()
        if self.registered and self.model.runtime.authoring:
            try:self.model.runtime.timeline_owner(self.panel,False,False)
            except RuntimeError as error:
                # Native may have already ended authoring between the last
                # status read and this unregister. A returned2040 dispatches
                # nothing. Always dispose our UI; Mod.stop still closes the
                # scene owner in its finally block. Unknown outcomes propagate.
                if self.model.runtime.uncertain or str(error)!='Scene asset adapter rejected request: 2040':raise
            self.registered=False
        try:return super().close()
        finally:
            if self.mirror is not None:
                self.mirror._render_call(self.mirror.widget,'Widget','RemoveFromParent')
                self.mirror.close_owned_tree();self.mirror=None
    def _paint_frame(self):
        original=self.panel
        for panel in (original,self.mirror):
            if panel is None:continue
            self.panel=panel
            try:
                with panel.paint_batch() if panel is not original else nullcontext():self._paint_panel()
            finally:self.panel=original

    def _paint_panel(self):
        self.panel.set_text(self.panel.title,'SCENE EDITOR | TIMELINE 30 FPS | Hold Right Alt for cursor | Home pins cursor | Backspace hides timeline')
        present={control.token for control in self.frame.controls}
        for i in range(self.panel.count):self.panel.set_visible(i,i in present and bool(next(c.label for c in self.frame.controls if c.token==i)))
        for control in self.frame.controls:
            i=control.token;self.panel.set_text(self.panel.labels[i],control.label);self.panel.set_enabled(i,control.enabled)
            if getattr(self.model,'sequence_timeline',False):
                highlighted=control.label.startswith(('> ','[ '))
                cache=getattr(self,'_sequence_highlights',{});self._sequence_highlights=cache
                if cache.get(i)!=highlighted:
                    self.panel._render_call(self.panel.buttons[i],'Button','SetBackgroundColor',InBackgroundColor=dict(R=.10 if highlighted else .08,G=.30 if highlighted else .12,B=.37 if highlighted else .2,A=.98))
                    cache[i]=highlighted
        self.panel.draw(self.model)
        if getattr(self.model,'sequence_timeline',False):
            self.panel._render_call(self.panel.scrubber,'Widget','SetVisibility',InVisibility=self.panel.visible)
            library=self.view.picker in ('sequence','sequences')
            for pane in self.panel.library_panes:self.panel._render_call(pane,'Widget','SetVisibility',InVisibility=self.panel.invisible if self.view.picker=='sequence' else self.panel.collapsed)
            self.panel.layout_sequence_field(library)
            self.panel.layout_sequence_library(self.view)
            for widget in (self.panel.library_back,self.panel.field,self.panel.field_back):
                self.panel._render_call(widget,'Widget','SetVisibility',InVisibility=(self.panel.invisible if library else self.panel.collapsed) if widget is self.panel.library_back else self.panel.visible if widget is self.panel.field else self.panel.invisible)
            editor=getattr(self.model,'editor',None);field=editor.field() if editor is not None and self.view.picker=='sequence' else None
            key=(self.view.picker,editor.revision if self.view.picker=='sequence' and editor else None,self.view.query if self.view.picker=='sequences' else None)
            if getattr(self,'_sequence_field_key',None)!=key:
                self.panel.set_field(self.view.query if self.view.picker=='sequences' else field[1] if field else '' if self.view.picker=='sequence' else f'{self.model.frame+self.model.subframe:g}');self._sequence_field_key=key
            return
        audio=bool(self.view.picker)
        hud=getattr(self.model,'hud',None)
        if hud is not None and getattr(hud,'library_hidden',False)!=audio:
            hud._render_call(hud.widget,'Widget','SetRenderOpacity',InOpacity=0. if audio else 1.)
            hud.library_hidden=audio
        self.panel._render_call(self.panel.library_back,'Widget','SetVisibility',InVisibility=self.panel.invisible if audio else self.panel.collapsed)
        for i,slots in enumerate(self.panel.category_slots):
            for slot in slots:self.panel.anchor(slot,.03+i*.24,.125 if audio else .72,render=True)
        for widget in (self.panel.field,self.panel.field_back):self.panel._render_call(widget,'Widget','SetVisibility',InVisibility=(self.panel.visible if widget is self.panel.field else self.panel.invisible) if audio else self.panel.collapsed)
        if audio:self.panel.set_field(self.view.query if self.view.picker in ('audio','sequences') else self.view.animation_query)
