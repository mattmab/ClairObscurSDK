"""Owned walking-dialogue playback with exact original completion receipts.

The reviewed initial profile supports Gustave/Sophie portrait IDs 0/9 and
emotion 0. A private data asset belongs to a noninteractive owned carrier;
the engine owns a deep copy of the lines and text. Native staging storage
remains pinned until explicit cleanup, including interrupted world retirement.
"""
import secrets,threading
from . import _story_inworld_wire as wire

SYSTEM='/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:'
WIDGET='/Game/UI/Widgets/HUD_Exploration/WBP_DialogNotifBox.WBP_DialogNotifBox_C:'
EMPTY='/Game/Gameplay/DialogueSystem/DialogueCharacters/DA_EmptyNameCharacter.DA_EmptyNameCharacter'

class InWorldDialogue:
    @property
    def _closed(self):
        # Playback outcome remains available in state after detachment. Domain
        # retirement separately needs the acknowledged native/carrier closure.
        return self.closed
    def __init__(self,parent):
        parent._check()
        capability=getattr(parent._session._transport,'story_inworld_dialogue_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Owned in-world dialogue SDK runtime required')
        self._scope=parent;self.carrier=None;self.scope=None;self.objects={};self.held=[]
        self.ticket=secrets.randbits(64) or 1;self.owner=0;self.asset_lease=0;self.system_lease=0
        self.state='new';self.attempted=False;self.detached=False;self.unknown=False;self.closed=False;self._thread=threading.get_ident()
        parent._register_native_owner(self);parent._close_before_descendants(self)
    def prepare(self,lines,pose):
        self._scope._check()
        if self.state!='new':raise RuntimeError('Ambient preparation is one-shot')
        from .story_npc import StoryNpc
        from .catalog import capture_matching
        from .picto_class_load import load_class
        from ._stable_lease import acquire_stable
        from .cinematics.original_game_action import controller_context
        self.state='preparing';self.carrier=StoryNpc(self._scope);self.scope=self.carrier.scope
        self.carrier.prepare(pose,EMPTY,visual_profile=None)
        self.owner=self.carrier.actor.owner._owner
        # Leave the carrier hidden, collision-free and noninteractive.
        cls=load_class(self.scope,'/Game/Dialogues/Data/BP_DA_IWD_data.BP_DA_IWD_data_C').return_value
        if cls is None:raise RuntimeError('Original ambient dialogue class unavailable')
        names=('SpawnObject','Default__GameplayStatics','PlayInWorldDialogue','IsPlayingSpecificInWorldDialogue','InterruptInWorldDialogue','OnAllDialogueLinesFinished','InterruptDialog')
        c=capture_matching(self.scope.pid,names=names,classes=('BP_DialogueSystemComponent_C',))
        created=self.carrier._spawn_speaker(c,cls);asset=created.return_value
        if asset is None or asset.outer_index!=self.carrier.npc.index or asset.class_name!='BP_DA_IWD_data_C':raise RuntimeError('Ambient factory returned another object')
        def hold(obj):
            held,_=acquire_stable(self.scope,obj);self.held.append(held);return held
        a=hold(asset);self.asset_lease=a._token
        ctx=controller_context(self.scope._session);controller=ctx['controller'][1]
        systems=[o for o in c.objects if o.class_name=='BP_DialogueSystemComponent_C' and o.outer_index==controller]
        if len(systems)!=1:raise RuntimeError('One current local-player dialogue system required')
        system=hold(systems[0]);self.system_lease=system._token
        self.objects=dict(carrier=self.carrier.npc,asset=a.object,system=system.object)
        for key,name,prefix in [('play','PlayInWorldDialogue',SYSTEM),('query','IsPlayingSpecificInWorldDialogue',SYSTEM),('interrupt','InterruptInWorldDialogue',SYSTEM),('finished','OnAllDialogueLinesFinished',WIDGET),('widget_interrupt','InterruptDialog',WIDGET)]:
            self.objects[key]=hold(c.find_path(prefix+name)).object
        self.lines=tuple(dict(line) for line in lines)
        # Stable retention of every optional UObject referenced by the frame.
        for line in self.lines:
            for key in ('dialogue_wave','sound','sound_table'):
                if line.get(key) is not None:line[key]=hold(line[key]).object
        self.packet=wire.encode(self.owner,self.ticket,self.asset_lease,self.system_lease,self.objects,lines=self.lines)
        self.state='prepared';return self
    def _send(self,mode):
        if threading.get_ident()!=self._thread:raise RuntimeError('Ambient playback requires its owning thread')
        if self.closed or self.unknown:raise RuntimeError('Ambient native owner is unavailable')
        packet=self.packet if mode==0 else wire.encode(self.owner,self.ticket,self.asset_lease,self.system_lease,self.objects,mode=mode)
        try:
            if mode in (2,3,4):
                # Cleanup remains available after its parent scope revokes new
                # work. Native session/token/world proofs still govern it.
                reply=self.scope._session._transport.command('mesh',packet)
            else:
                with self.scope._lease_context():reply=self.scope._session._transport.command('mesh',packet)
            return wire.decode(packet,bytes.fromhex(reply['mesh_packet']))
        except wire.InWorldError as error:
            if error.native_error==3931:self.unknown=True
            raise
        except BaseException:
            self.unknown=True;raise
    def start(self):
        self._scope._check()
        if self.state!='prepared' or self.attempted:raise RuntimeError('Ambient dispatch is never replayed')
        self.attempted=True;self.state='dispatching'
        try:self.state=self._send(0)
        except wire.InWorldError as error:
            if error.native_error in (3930,3932):self.attempted=False;self.state='prepared'
            raise
        return self.state
    def poll(self):
        self._scope._check()
        if not self.attempted:raise RuntimeError('Ambient playback has not started')
        self.state=self._send(1);return self.state
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.attempted and not self.detached:
            try:
                if self.state not in ('completed','not_played','interrupted','world_retired'):
                    self.state=self._send(3)
                    if self.state=='playing':return False
                self.state=self._send(2)
                self.detached=True
            except wire.InWorldError as error:
                if error.native_error in (3930,3932):return False
                raise
        if self.carrier is not None and not self.carrier.close():return False
        self.closed=True;return True
    def retire_world(self):
        if self.closed:return True
        if self.unknown:return False
        if self.attempted and not self.detached:
            try:self.state=self._send(4);self.detached=True
            except wire.InWorldError as error:
                if error.native_error==3930:return False
                raise
        if self.carrier is not None and not self.carrier.retire_world():return False
        self.closed=True;return True
