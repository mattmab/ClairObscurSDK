"""Explicitly owned, selected-save adapters for original narrative interactions.

These APIs leave the original choices, actors, quest logic and walking triggers
in place. Retirement restores borrowed asset arrays and detaches all hooks.
"""
import secrets
from . import _story_original_wire as wire
from ._reader import shared_operation

SYSTEM='/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:'
ROOT='/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/'

class _Owner:
    def __init__(self,parent,key,*,resources=None,scene=None):
        parent._check()
        if getattr(parent._session._transport,'story_original_narrative_protocol',0)!=1:
            raise RuntimeError('Original narrative adapters require SDK runtime 291')
        from ._scope import SessionScope
        self._scope=parent;self.scope=SessionScope(parent);self.key=key
        self.resources=resources;self.scene=scene
        self.owner=secrets.randbits(64) or 1;self.held=[];self._held_by_identity={};self.started=False;self.closed=False;self.unknown=False
        parent._register_native_owner(self);parent._close_before_descendants(self)
    @property
    def state(self):return 'closed' if self.closed else 'unknown' if self.unknown else 'active'
    def hold(self,obj):
        from ._stable_lease import acquire_stable
        if obj is None:raise RuntimeError('Original narrative dependency unavailable')
        self.scope._check()
        if self.resources is not None:
            held=self.resources.hold(obj);self.held.append(held);return held
        key=(obj.pid,obj.index,obj.serial,obj.address)
        previous=self._held_by_identity.get(key) if obj.serial>0 else None
        if previous is not None and previous.active is True:return previous
        held,_=acquire_stable(self.scope,obj);self.held.append(held)
        stable=held.object;self._held_by_identity[(stable.pid,stable.index,stable.serial,stable.address)]=held
        return held
    def send(self,packet):
        if self.closed or self.unknown:raise RuntimeError('Original narrative owner is unavailable')
        try:
            reply=self.scope._session._transport.command('mesh',packet)
            return wire.decode(packet,bytes.fromhex(reply['mesh_packet']))
        except wire.OriginalNarrativeError as error:
            if error.code in (3951,3961,3971):self.unknown=True
            raise
        except BaseException:
            self.unknown=True;raise
    def context(self):
        from .story_save_identity import observe
        from .catalog import capture_matching
        if self.scene is not None:
            self.gi=self.hold(self.scene.gi)
            return self.scene.catalog
        _,_,_,_,gi,_=observe(self.scope)
        self.gi=self.hold(gi)
        return capture_matching(self.scope.pid,names=('StartRichDialogueLines','EndDialogue','IsPlayingSpecificInWorldDialogue'),classes=('BP_DialogueSystemComponent_C',))

class OriginalDialogueRewrites(_Owner):
    def prepare(self,profiles,*,sound_overrides=None):
        """Profiles: (original class path, ((source string-table key,text), ...))."""
        from .picto_class_load import load_class
        if self.started or self.held:raise RuntimeError('Original rewrite preparation is one-shot')
        self.profiles=[];self.sounds=[]
        with shared_operation(self.scope.pid):
            c=self.context();self.function=self.hold(c.find_path(SYSTEM+'StartRichDialogueLines'))
            from .catalog import capture_matching
            text=self.scene.catalog if self.scene is not None else capture_matching(self.scope.pid,names=('Default__KismetTextLibrary','StringTableIdAndKeyFromText'))
            self.text_cdo=self.hold(text.find_path('/Script/Engine.Default__KismetTextLibrary'))
            self.text_query=self.hold(text.find_path('/Script/Engine.KismetTextLibrary:StringTableIdAndKeyFromText'))
            for i,(path,texts) in enumerate(profiles):
                if i>=8:raise ValueError('At most eight original dialogue profiles')
                source=self.hold(self.resources.load(path,cls=True) if self.resources is not None else load_class(self.scope,path).return_value)
                self.profiles.append(source)
                sound,mask=(sound_overrides or {}).get(i,(None,0))
                if sound:
                    from .assets import load_asset
                    sound=self.hold(self.resources.load(sound) if self.resources is not None else load_asset(self.scope,sound).return_value)
                self.sounds.append((sound,mask))
                self.send(wire.rewrite(self.owner,self.function,self.gi,source,self.key,i,self.text_cdo,self.text_query,texts=texts,sound=sound,sound_mask=mask));self.started=True
        return self
    def counts(self):
        return tuple(self.send(wire.rewrite(self.owner,self.function,self.gi,source,self.key,i,self.text_cdo,self.text_query,mode=1,sound=self.sounds[i][0],sound_mask=self.sounds[i][1])) for i,source in enumerate(self.profiles))
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:
            self.send(wire.rewrite(self.owner,self.function,self.gi,self.profiles[0],self.key,0,self.text_cdo,self.text_query,mode=2,sound=self.sounds[0][0],sound_mask=self.sounds[0][1]));self.started=False
        self.scope.close();self.closed=True;return True

class OriginalFlowerContinuation(_Owner):
    def prepare(self):
        from .picto_class_load import load_class
        if self.started or self.held:raise RuntimeError('Original continuation preparation is one-shot')
        with shared_operation(self.scope.pid):
            c=self.context();self.function=self.hold(c.find_path(SYSTEM+'EndDialogue'))
            name='BP_Dialogue_Gardens_GustaveFlower'
            path=ROOT+name+'.'+name+'_C'
            self.source=self.hold(self.resources.load(path,cls=True) if self.resources is not None else load_class(self.scope,path).return_value)
            self.sequence=0;self.send(self.packet(0));self.started=True
        return self
    def packet(self,mode):
        return wire.continuation(self.owner,self.function,self.gi,self.source,self.key,mode=mode,sequence=self.sequence)
    def poll(self):
        self.scope._check();receipt=self.send(self.packet(1));self.sequence=receipt['sequence'];return receipt
    def finish(self):
        # Called once after the injected final line actually completes. The
        # native adapter dispatches the copied original End arguments once.
        return self.send(self.packet(2))
    def cancel(self):
        """Release an owned deferred dialogue during disable/retirement only."""
        return self.send(self.packet(4))
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:
            try:self.send(self.packet(3))
            except wire.OriginalNarrativeError as error:
                if error.code==3960:return False
                raise
            self.started=False
        self.scope.close();self.closed=True;return True

class OriginalAmbientOverlay(_Owner):
    def prepare(self,path,lines,*,expected_count):
        from .assets import load_asset
        from .catalog import capture_selected
        from .cinematics.controller_anchor import for_scope
        if self.started or self.held:raise RuntimeError('Original ambient overlay preparation is one-shot')
        with shared_operation(self.scope.pid):
            c=self.context();ctx=self.scene.context if self.scene is not None else for_scope(self.scope).context()
            world_id=tuple(ctx['world'][1:])
            if self.scene is not None:self.world=self.scene.world
            else:
                wc=capture_selected(self.scope.pid,(world_id,));self.world=wc.by_index[world_id[0]]
            # Retain only process assets. A strong World/controller/component
            # reference here would prevent the game's map collection.
            controller=ctx['controller'][1]
            systems=[o for o in c.objects if o.class_name=='BP_DialogueSystemComponent_C' and o.outer_index==controller]
            if len(systems)!=1:raise RuntimeError('One local original dialogue system required')
            transient=None if self.scene is not None else self.hold(systems[0]);self.system=self.scene.system if self.scene is not None else transient.object
            self.query=self.hold(c.find_path(SYSTEM+'IsPlayingSpecificInWorldDialogue')).object
            self.asset=self.hold(self.resources.load(path) if self.resources is not None else load_asset(self.scope,path).return_value)
            self.lines=tuple(dict(line) for line in lines);self.expected_count=expected_count
            for line in self.lines:
                for name in ('dialogue_wave','sound','sound_table'):
                    if line.get(name) is not None:line[name]=self.hold(line[name]).object
            self.send(self.packet(0));self.started=True
            # Stabilization only. Native stores a weak generation identity and
            # does not protect this transient component lease.
            if transient is not None:transient.release()
        return self
    def packet(self,mode):
        return wire.ambient(self.owner,self.asset,self.gi,self.world,self.system,self.query,self.key,self.expected_count,mode=mode,lines=self.lines if mode==0 else ())
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:
            try:self.send(self.packet(2))
            except wire.OriginalNarrativeError as error:
                if error.code==3972:return False
                raise
            self.started=False
        self.scope.close();self.closed=True;return True

class OriginalRewardExtensions(_Owner):
    def prepare(self,definitions,*,origins,extras):
        from . import _story_reward_wire
        from .catalog import capture_matching
        from .picto_class_load import load_class
        from .cinematics.controller_anchor import for_scope
        if self.started or self.held:raise RuntimeError('Original reward extension preparation is one-shot')
        if not definitions.started or definitions.closed or definitions.unknown:raise RuntimeError('Verified cosmetic definitions must be registered first')
        self.definitions=definitions;self.origins=tuple(origins);self.extras=tuple(tuple(r) for r in extras)
        with shared_operation(self.scope.pid):
            c=self.context();ctx=self.scene.context if self.scene is not None else for_scope(self.scope).context();controller=ctx['controller'][1]
            candidates=[o for o in c.objects if o.class_name=='BP_DialogueSystemComponent_C' and o.outer_index==controller]
            if len(candidates)!=1:raise RuntimeError('One original local dialogue system required')
            transient=None if self.scene is not None else self.hold(candidates[0]);self.system=self.scene.system if self.scene is not None else transient.object
            c=self.scene.catalog if self.scene is not None else capture_matching(self.scope.pid,names=('AddItemToInventory',))
            self.function=self.hold(c.find_path('/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_InventoryManager.AC_jRPG_InventoryManager_C:AddItemToInventory'))
            self.sources=tuple(self.hold(self.resources.load(ROOT+n+'.'+n+'_C',cls=True) if self.resources is not None else load_class(self.scope,ROOT+n+'.'+n+'_C').return_value) for n in ('BP_Dialogue_Gardens_GustaveFlower','BP_Dialogue_Jules'))
            self.send_reward(0);self.started=True
            if transient is not None:transient.release()
        return self
    def send_reward(self,mode):
        from . import _story_reward_wire as reward_wire
        packet=reward_wire.encode(self.owner,self.gi,self.system,self.function,self.sources,self.definitions.owner,self.key,self.origins,self.extras,mode=mode)
        try:
            result=self.scope._session._transport.command('mesh',packet)
            return reward_wire.decode(packet,bytes.fromhex(result['mesh_packet']))
        except wire.OriginalNarrativeError as error:
            if error.code==4001:self.unknown=True
            raise
        except BaseException:
            self.unknown=True;raise
    def counts(self):return self.send_reward(1)
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self.send_reward(2);self.started=False
        self.scope.close();self.closed=True;return True
