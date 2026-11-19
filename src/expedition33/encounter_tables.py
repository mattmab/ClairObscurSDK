"""Explicit additive encounter/enemy rows, bound to the selected save and composite owner."""
import re,secrets,struct
from . import _story_item_wire as wire
from .story_original import _Owner

TARGETS={'encounter':'DT_jRPG_Encounters','enemy':'DT_jRPG_Enemies'}
KIND=2064;REWARD=2068;TAIL=2164

def validate_profiles(profiles):
    if type(profiles)is not dict or not 1<=len(profiles)<=2:raise ValueError('One or two encounter table profiles required')
    kinds=set();result={}
    for asset,profile in profiles.items():
        if type(asset)is not str or re.fullmatch(r'[A-Za-z0-9_]{1,95}',asset) is None or type(profile)is not dict:
            raise ValueError('Encounter source asset ID')
        if set(profile)!={'kind','source_package','row','required_reward'} or profile['kind'] not in TARGETS or profile['kind'] in kinds:
            raise ValueError('One encounter and one enemy registry may be active')
        kinds.add(profile['kind']);package=profile['source_package']
        if type(package)is not str or len(package)>=256 or re.fullmatch(r'/Game/SDK/(?:[A-Za-z0-9_]+/)*'+re.escape(asset),package) is None:
            raise ValueError('Encounter table must name its SDK source asset')
        for field in ('row','required_reward'):
            value=profile[field]
            if type(value)is not str or (not value and field=='row') or (value and re.fullmatch(r'[A-Za-z0-9_]{1,95}',value) is None):
                raise ValueError('Encounter row or required reward ID')
        result[asset]=dict(profile)
    return result

def profile_key(profiles):return tuple((asset,tuple(sorted(row.items()))) for asset,row in sorted(profiles.items()))

def warm(resources,profiles):
    """Retain immutable tables at title; publish no rows or selected-save state."""
    profiles=validate_profiles(profiles)
    resources.scope._check()
    cache=getattr(resources,'_encounter_table_inputs',None)
    if cache is None:cache={};resources._encounter_table_inputs=cache
    key=profile_key(profiles);journal=cache.get(key)
    if journal is not None:
        if not journal['ready']:raise RuntimeError('Encounter table input preparation failed; not replayed')
        if any(not held.active for pair in journal['rows'].values() for held in pair):
            raise RuntimeError('Encounter table dependency lease expired')
        return {asset:tuple(held.object for held in pair) for asset,pair in journal['rows'].items()}
    journal=dict(ready=False,rows={},error=None);cache[key]=journal
    try:
        for asset,profile in profiles.items():
            target=TARGETS[profile['kind']]
            source=resources.hold(resources.load(profile['source_package']+'.'+asset))
            destination=resources.hold(resources.load('/Game/jRPGTemplate/Datatables/'+target+'.'+target))
            journal['rows'][asset]=(source,destination)
        journal['ready']=True
        return {asset:tuple(held.object for held in pair) for asset,pair in journal['rows'].items()}
    except BaseException as error:journal['error']=str(error);raise
def validate(data):
    if type(data)is not bytes or len(data)!=wire.SIZE or struct.unpack_from('<I',data,4)[0]!=254:raise ValueError('Encounter table packet')
    wire.identity(data,2024)
    if not struct.unpack_from('<Q',data,2040)[0] or struct.unpack_from('<I',data,2048)[0]!=0xe33c5701:raise ValueError('Encounter selected save identity')
    copy=bytearray(data);struct.pack_into('<I',copy,4,241);copy[2024:TAIL]=bytes(TAIL-2024);wire.validate(bytes(copy))
    package=data[136:392].split(b'\0',1)[0].decode('ascii');asset=data[392:488].split(b'\0',1)[0].decode('ascii')
    row=data[488:584].split(b'\0',1)[0].decode('ascii')
    kind=struct.unpack_from('<I',data,KIND)[0];reward=data[REWARD:TAIL].split(b'\0',1)[0]
    if kind>1 or data[REWARD:TAIL]!=reward.ljust(96,b'\0') or len(reward)==96 or struct.unpack_from('<I',data,124)[0]!=1:
        raise ValueError('Encounter table kind, row count or reward padding')
    validate_profiles({asset:dict(kind=('encounter','enemy')[kind],source_package=package,row=row,required_reward=reward.decode('ascii'))})

def packet(owner,row,gi,key,mode):
    profile=validate_profiles({row['asset']:row['profile']})[row['asset']]
    data=bytearray(wire.definitions(owner,row['target'],row['source'],row['map_class'],row['map_add'],
        profile['source_package'],row['asset'],(profile['row'],),mode=mode))
    struct.pack_into('<I',data,4,254);wire.put_id(data,2024,gi.object);struct.pack_into('<Q',data,2040,gi._token)
    if len(key)!=32:raise ValueError('Encounter story save identity')
    struct.pack_into('<4I',data,2048,*(int(key[i:i+8],16) for i in range(0,32,8)))
    struct.pack_into('<I',data,KIND,profile['kind']=='enemy')
    data[REWARD:TAIL]=profile['required_reward'].encode('ascii').ljust(96,b'\0')
    result=bytes(data);validate(result);return result
def decode(sent,reply):
    validate(sent)
    if type(reply)is not bytes or len(reply)!=len(sent):raise RuntimeError('Encounter registry acknowledgement size')
    error,state=struct.unpack_from('<2I',reply,8);copy=bytearray(reply);copy[8:16]=sent[8:16];copy[128:136]=sent[128:136]
    if bytes(copy)!=sent:raise RuntimeError('Encounter registry acknowledgement context changed')
    if error:raise wire.OriginalNarrativeError(error)
    if state!=struct.unpack_from('<I',sent,120)[0]+1:raise RuntimeError('Encounter registry acknowledgement state')
    old,new=struct.unpack_from('<2I',reply,128)
    if state in (1,2) and (old<1 or new!=old+1):raise RuntimeError('Encounter registry must add exactly one row')
    return {'original_rows':old,'registered_rows':new}

class EncounterTables:
    # Owned by the caller composing a battle, which closes its battle
    # before this borrowed registry and the metadata scope beneath it.
    def __init__(self,parent,key,definitions,*,profiles,resources=None):
        self.profiles=validate_profiles(profiles)
        if getattr(parent._session._transport,'story_trial_tables_protocol',0)!=2:raise RuntimeError('Encounter tables require protocol 2')
        from ._scope import SessionScope
        self.scope=SessionScope(parent);self.key=key;self.definitions=definitions
        self.resources=resources;self.held=[];self._held_by_identity={};self.rows=[];self.unknown=False;self.closed=False
        self.inputs_ready=False;self.resolution_attempted=False;self.preparation_error=None
    def hold(self,obj):return _Owner.hold(self,obj)
    @property
    def ready(self):
        return bool(not self.closed and not self.unknown and self.preparation_error is None and
                    self.inputs_ready and len(self.rows)==len(self.profiles) and
                    all(row['acknowledged'] and row['started'] for row in self.rows))
    def preflight(self):
        from .story_save_identity import observe
        from .story_preflight import observe as read_preflight
        from .story_items import load_resource_asset
        from .assets import load_asset
        if self.closed or self.unknown or self.preparation_error is not None:raise RuntimeError('Encounter registry preparation unavailable')
        if self.inputs_ready:return self
        if self.resolution_attempted:raise RuntimeError('Encounter input resolution was already attempted')
        if self.resources is not None and self.resources.scope._session is not self.scope._session:
            raise RuntimeError('Encounter resources belong to another session')
        gi=getattr(self.resources,'gi',None)
        if gi is None:*_,gi,_=read_preflight(observe,self.scope)
        self.resolution_attempted=True
        try:
            inputs=warm(self.resources,self.profiles) if self.resources is not None else None
            self.gi=self.hold(gi)
            map_class=self.hold(self.definitions.map_class.object);map_add=self.hold(self.definitions.map_add.object)
            for asset,profile in self.profiles.items():
                target=TARGETS[profile['kind']]
                row=dict(owner=secrets.randbits(64)or 1,asset=asset,profile=profile,started=False,attempted=False,acknowledged=False,receipt=None)
                self.rows.append(row)
                if inputs is not None:
                    source,destination=inputs[asset]
                    row['source']=self.hold(source);row['target']=self.hold(destination)
                else:
                    row['source']=self.hold(load_resource_asset(self.scope,profile['source_package']+'.'+asset).return_value)
                    row['target']=self.hold(load_asset(self.scope,'/Game/jRPGTemplate/Datatables/'+target+'.'+target).return_value)
                row['map_class']=map_class;row['map_add']=map_add
            # Every immutable dependency and both selected-save packets must be
            # resolved/validated before the first table mutation is attempted.
            for row in self.rows:packet(row['owner'],row,self.gi,self.key,0)
            self.inputs_ready=True
        except BaseException as error:self.preparation_error=str(error);raise
        return self
    def prepare(self):
        self.preflight()
        for row in self.rows:
            if row['acknowledged']:continue
            if row['attempted']:raise RuntimeError('Encounter row outcome unresolved; not replayed')
            row['attempted']=True
            try:
                row['receipt']=self.send(row,0);row['started']=True;row['acknowledged']=True
            except BaseException as error:self.preparation_error=str(error);raise
        return self
    def send(self,row,mode):
        sent=packet(row['owner'],row,self.gi,self.key,mode)
        try:return decode(sent,bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet']))
        except wire.OriginalNarrativeError as error:
            if error.code==4241:self.unknown=True
            raise
        except BaseException:self.unknown=True;raise
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        for row in reversed(self.rows):
            if not row['started']:continue
            try:self.send(row,2)
            except wire.OriginalNarrativeError as error:
                if error.code==4242:return False
                raise
            row['started']=False
        self.scope.close();self.closed=True;return True
