"""Owned vanilla join-action data, replacing cooked recruitment orchestration."""
import re,struct
from .story_original import _Owner
from ._story_original_wire import identity,put_id,OriginalNarrativeError

SIZE=20984
CLASS='/Game/Gameplay/GameActionsSystem/SetCurrentParty/BP_GameAction_CharacterJoinGroup.BP_GameAction_CharacterJoinGroup_C'

def packet(owner,action,gi,executor,key,mode=0,*,character):
    character=character_id(character)
    data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,258,0,0,owner)
    for n,obj in enumerate((action,gi,executor)):
        put_id(data,24+n*16,obj.object);struct.pack_into('<Q',data,72+n*8,obj._token)
    if len(key)!=32:raise ValueError('Selected-save key length')
    struct.pack_into('<4I2I',data,96,*(int(key[i:i+8],16) for i in range(0,32,8)),mode,0)
    data[120:216]=character.encode("ascii").ljust(96,b"\0")
    result=bytes(data);validate(result);return result

def character_id(value):
    """Validate a row ID supplied by the consumer; no character is implicit."""
    if type(value) is not str or re.fullmatch(r'[A-Za-z0-9_]{1,95}',value) is None:
        raise ValueError('Character ID must contain 1 to 95 ASCII letters, digits or underscores')
    return value

def validate(data):
    if type(data)is not bytes or len(data)!=SIZE:raise ValueError('Party join data packet size')
    version,op,error,state,owner=struct.unpack_from('<4IQ',data)
    if (version,op,error,state)!=(3,258,0,0) or not owner:raise ValueError('Party join data header')
    for offset in (24,40,56):identity(data,offset)
    if not all(struct.unpack_from('<3Q',data,72)) or struct.unpack_from('<I',data,96)[0]!=0xe33c5701:raise ValueError('Selected party save leases')
    mode,reserved=struct.unpack_from('<2I',data,112)
    if mode>2 or reserved or any(data[216:]):raise ValueError('Party join data mode or padding')
    raw=data[120:216];name=raw.split(b'\0',1)[0]
    if raw!=name.ljust(96,b'\0'):raise ValueError('Party character ID padding')
    character_id(name.decode('ascii'))

def decode(sent,reply):
    validate(sent)
    if type(reply)is not bytes or len(reply)!=SIZE:raise RuntimeError('Party join data acknowledgement size')
    error,state=struct.unpack_from('<2I',reply,8);copy=bytearray(reply);copy[8:16]=sent[8:16]
    if bytes(copy)!=sent:raise RuntimeError('Party join data acknowledgement identity changed')
    if error:raise OriginalNarrativeError(error)
    if state!=struct.unpack_from('<I',sent,112)[0]+1:raise RuntimeError('Party join data acknowledgement state')
    return state

class PartyJoinData(_Owner):
    def __init__(self,parent,key,*,character,resources=None):
        self.character=character_id(character)
        if getattr(parent._session._transport,'story_party_join_data_protocol',0)!=2:
            raise RuntimeError('Generic party recruitment requires party join protocol 2')
        super().__init__(parent,key,resources=resources)
        self.planner=None
    def local_hold(self,obj):
        from ._stable_lease import acquire_stable
        held,_=acquire_stable(self.scope,obj);self.held.append(held);return held
    def prepare(self,executor):
        from .catalog import capture_matching,capture_selected
        from .picto_class_load import load_class
        from ._reader import shared_operation
        if self.started or self.held:raise RuntimeError('Party join data preparation is one-shot')
        with shared_operation(self.scope.pid):
            self.context()
            cls=self.resources.load(CLASS,cls=True) if self.resources is not None else load_class(self.scope,CLASS).return_value
            c=capture_matching(self.scope.pid,names=('Default__GameplayStatics','SpawnObject'))
            library=c.find_path('/Script/Engine.Default__GameplayStatics');function=c.find_path('/Script/Engine.GameplayStatics:SpawnObject')
            selected=capture_selected(self.scope.pid,tuple((o.index,o.serial,o.address) for o in (library,function,cls,self.gi.object)))
            self.planner=self.scope.invocation_planner(catalog=selected,selected_results=True)
            with self.planner.prepare(library,function,ObjectClass=cls,Outer=self.gi.object).invoke(fresh_results=True) as created:
                action=created.return_value
                if action is None or action.class_name!='BP_GameAction_CharacterJoinGroup_C' or action.outer_index!=self.gi.object.index or action.object_flags&0x30:
                    raise RuntimeError('Party join factory returned another object')
                self.action=self.local_hold(action)
            self.executor=self.local_hold(executor)
            self.send(0);self.started=True
        return self
    def send(self,mode):
        sent=packet(self.owner,self.action,self.gi,self.executor,self.key,mode,character=self.character)
        try:return decode(sent,bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet']))
        except OriginalNarrativeError as error:
            if error.code==4271:self.unknown=True
            raise
        except BaseException:self.unknown=True;raise
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:
            try:self.send(2)
            except OriginalNarrativeError as error:
                if error.code==4272:return False
                raise
            self.started=False
        if self.planner is not None:self.planner.close();self.planner=None
        self.scope.close();self.closed=True;return True
