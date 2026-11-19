"""Build owned vanilla TriggerBattle data from explicit consumer parameters."""
import struct
from .story_original import _Owner
from ._story_original_wire import identity,put_id,OriginalNarrativeError
from . import _encounter_action_profile as profiles
SIZE=20984
CLASS='/Game/Gameplay/GameActionsSystem/TriggerBattle/BP_GameAction_TriggerBattle.BP_GameAction_TriggerBattle_C'
METADATA=('/Game/Gameplay/Battle/FBattleStartParams.FBattleStartParams',
          '/Script/Engine.Default__KismetSystemLibrary',
          '/Script/Engine.KismetSystemLibrary:Conv_ObjectToSoftObjectReference',
          '/Script/Engine.Default__GameplayStatics',
          '/Script/Engine.GameplayStatics:SpawnObject')

def warm(resources,profile):
    """Retain source class/assets/schema at title without constructing an action."""
    profile=profiles.validate_profile(profile)
    resources.scope._check()
    cache=getattr(resources,'_encounter_action_inputs',None)
    if cache is None:cache={};resources._encounter_action_inputs=cache
    key=profiles.encode(profile);journal=cache.get(key)
    if journal is not None:
        if not journal['ready']:raise RuntimeError('Encounter parameter input preparation failed; not replayed')
        if any(not held.active for held in journal['objects']):raise RuntimeError('Encounter parameter dependency lease expired')
        return tuple(held.object for held in journal['objects'])
    from .catalog import capture_matching
    journal=dict(ready=False,objects=[],error=None);cache[key]=journal
    try:
        for path,cls in ((CLASS,True),(profile['table'],False),(profile['music'],False)):
            journal['objects'].append(resources.hold(resources.load(path,cls=cls)))
        catalog=capture_matching(resources.scope.pid,names=tuple(path.rsplit('.',1)[-1].split(':')[-1] for path in METADATA))
        for path in METADATA:journal['objects'].append(resources.hold(catalog.find_path(path)))
        journal['ready']=True
        return tuple(held.object for held in journal['objects'])
    except BaseException as error:journal['error']=str(error);raise

def packet(owner,held,key,mode=0,*,profile):
    if len(held)!=8:raise ValueError('Exact encounter data dependencies required')
    data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,260,0,0,owner)
    for n,obj in enumerate(held):put_id(data,24+n*16,obj.object);struct.pack_into('<Q',data,152+n*8,obj._token)
    if len(key)!=32:raise ValueError('Selected-save key length')
    struct.pack_into('<4I2I',data,216,*(int(key[i:i+8],16) for i in range(0,32,8)),mode,0)
    data[profiles.CONFIG:profiles.END]=profiles.encode(profile)
    result=bytes(data);validate(result);return result
def validate(data):
    if type(data)is not bytes or len(data)!=SIZE:raise ValueError('Encounter data packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',data)
    if (version,op,error,state)!=(3,260,0,0) or not owner:raise ValueError('Encounter data header')
    for n in range(8):identity(data,24+n*16)
    if not all(struct.unpack_from('<8Q',data,152)) or struct.unpack_from('<I',data,216)[0]!=0xe33c5701:raise ValueError('Selected encounter save leases')
    mode,reserved=struct.unpack_from('<2I',data,232)
    if mode>2 or reserved or any(data[profiles.END:]):raise ValueError('Encounter action mode or padding')
    profiles.decode(data[profiles.CONFIG:profiles.END])
def decode(sent,reply):
    validate(sent)
    if type(reply)is not bytes or len(reply)!=SIZE:raise RuntimeError('Encounter data acknowledgement size')
    error,state=struct.unpack_from('<2I',reply,8);copy=bytearray(reply);copy[8:16]=sent[8:16]
    if bytes(copy)!=sent:raise RuntimeError('Encounter data acknowledgement identity changed')
    if error:raise OriginalNarrativeError(error)
    if state!=struct.unpack_from('<I',sent,232)[0]+1:raise RuntimeError('Encounter data acknowledgement state')
    return state

class EncounterActionData(_Owner):
    def __init__(self,parent,key,*,profile,resources=None):
        self.profile=profiles.validate_profile(profile)
        if getattr(parent._session._transport,'story_trial_data_protocol',0)!=2:
            raise RuntimeError('Owned encounter actions require protocol 2')
        super().__init__(parent,key,resources=resources);self.planner=None
        self.preparation_attempted=False;self.creation_attempted=False;self.creation_returned=False;self.preparation_error=None
    def prepare(self):
        from .catalog import capture_matching,capture_selected
        from .picto_class_load import load_class
        from .story_items import load_resource_asset
        from .assets import load_asset
        from ._stable_lease import acquire_stable
        from ._reader import shared_operation
        if self.preparation_attempted or self.started or self.held:raise RuntimeError('Encounter data preparation is one-shot')
        self.preparation_attempted=True
        try:
            with shared_operation(self.scope.pid):
                if self.resources is not None:
                    if self.resources.scope._session is not self.scope._session:raise RuntimeError('Encounter resources belong to another session')
                    gi=getattr(self.resources,'gi',None)
                    if gi is None:raise RuntimeError('Prepared encounter GameInstance unavailable')
                    self.gi=self.hold(gi)
                    cls,table,music,structure,library,conversion,statics,spawn=warm(self.resources,self.profile)
                    cls,table,music,structure,library,conversion=(self.hold(obj) for obj in (cls,table,music,structure,library,conversion))
                else:
                    self.context()
                    cls=self.hold(load_class(self.scope,CLASS).return_value)
                    table=self.hold((load_resource_asset if self.profile['table'].startswith('/Game/SDK/') else load_asset)(self.scope,self.profile['table']).return_value)
                    music=self.hold((load_resource_asset if self.profile['music'].startswith('/Game/SDK/') else load_asset)(self.scope,self.profile['music']).return_value)
                    c=capture_matching(self.scope.pid,names=('FBattleStartParams','Default__GameplayStatics','SpawnObject','Default__KismetSystemLibrary','Conv_ObjectToSoftObjectReference'))
                    structure,library,conversion=(self.hold(c.find_path(path)) for path in METADATA[:3])
                    statics,spawn=(c.find_path(path) for path in METADATA[3:])
                selected=capture_selected(self.scope.pid,tuple((o.index,o.serial,o.address) for o in (statics,spawn,cls.object,self.gi.object)))
                construction=getattr(self.scope._session,'_story_construction_resources',None)
                self.planner=(construction.movement_planner(self.scope,selected) if construction is not None else
                              self.scope.invocation_planner(catalog=selected,selected_results=True))
                call=self.planner.prepare(statics,spawn,ObjectClass=cls.object,Outer=self.gi.object)
                self.creation_attempted=True
                with call.invoke(fresh_results=True) as created:
                    self.creation_returned=True
                    obj=created.return_value
                    if obj is None or obj.class_name!='BP_GameAction_TriggerBattle_C' or obj.outer_index!=self.gi.object.index or obj.object_flags&0x30:
                        raise RuntimeError('Encounter action factory returned another object')
                    action,_=acquire_stable(self.scope,obj);self.held.append(action)
                self.action=action;self.root=cls;self.dependencies=(action,cls,structure,table,self.gi,music,library,conversion)
                self.send(0);self.started=True
        except BaseException as error:
            self.preparation_error=str(error)
            if self.creation_attempted and (not self.creation_returned or not hasattr(self,'action')):self.unknown=True
            raise
        return self
    def send(self,mode):
        sent=packet(self.owner,self.dependencies,self.key,mode,profile=self.profile)
        try:return decode(sent,bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet']))
        except OriginalNarrativeError as error:
            if error.code==4291:self.unknown=True
            raise
        except BaseException:self.unknown=True;raise
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:
            try:self.send(2)
            except OriginalNarrativeError as error:
                if error.code==4292:return False
                raise
            self.started=False
        if self.planner is not None:self.planner.close();self.planner=None
        self.scope.close();self.closed=True;return True
