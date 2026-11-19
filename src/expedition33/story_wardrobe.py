"""Selected-save native wardrobe extension for a recruited character.

No item grants, party changes or save writes. The original wardrobe owns equip
and persistence. Only private preview components and menu routing are added.
"""
import struct
from .story_original import _Owner
from ._story_original_wire import put_id,identity,OriginalNarrativeError
from ._story_wardrobe_profile import INPUTS
from ._wardrobe_config import encode as encode_profile,decode as decode_profile,inputs as profile_inputs
SIZE=20984
COUNT=len(INPUTS)
LEASES=24+COUNT*16
GUID=LEASES+COUNT*8
MODE=GUID+16
RESULT=MODE+4
PROFILE=RESULT+16
TAIL=PROFILE+2616

def warm(resources,*,profile):
    """Title-time immutable dependencies; no save/menu hooks or actor spawns."""
    config=encode_profile(profile);inputs=profile_inputs(profile)
    cache=getattr(resources,'_wardrobe_dependencies',None)
    if cache is None:cache={};resources._wardrobe_dependencies=cache
    previous=cache.get(config)
    if previous is not None:
        if not all(o.active for o in previous):raise RuntimeError('Wardrobe resource lease expired')
        return tuple(o.object for o in previous)
    from .catalog import capture_matching
    for row in inputs:
        if row['kind'] in ('class','asset') and row['path'].startswith('/Game/'):resources.load(row['path'],cls=row['kind']=='class')
    names=tuple(r['path'].rsplit(':',1)[-1].rsplit('.',1)[-1] for r in inputs if r['kind']!='gi')
    catalog=capture_matching(resources.scope.pid,names=names)
    held=tuple(resources.hold(catalog.find_path(r['path'])) for r in inputs if r['kind']!='gi')
    cache[config]=held
    return tuple(o.object for o in held)

def validate(data):
    if type(data)is not bytes or len(data)!=SIZE or struct.unpack_from('<4I',data)!=(3,268,0,0) or not struct.unpack_from('<Q',data,16)[0]:raise ValueError('Wardrobe request header')
    for at in range(24,LEASES,16):identity(data,at)
    if not all(struct.unpack_from('<'+str(COUNT)+'Q',data,LEASES)) or struct.unpack_from('<I',data,GUID)[0]!=0xe33c5701 or struct.unpack_from('<I',data,MODE)[0]>5 or any(data[RESULT:PROFILE]) or any(data[TAIL:]):raise ValueError('Wardrobe request ownership/padding')
    decode_profile(data[PROFILE:TAIL])

def decode(sent,reply):
    validate(sent)
    if type(reply)is not bytes or len(reply)!=SIZE:raise RuntimeError('Wardrobe acknowledgement extent')
    clean=bytearray(reply);clean[8:16]=sent[8:16];clean[RESULT:RESULT+16]=sent[RESULT:RESULT+16]
    if clean!=sent:raise RuntimeError('Wardrobe acknowledgement context changed')
    error,state=struct.unpack_from('<2I',reply,8)
    if error:raise OriginalNarrativeError(error)
    if state!=struct.unpack_from('<I',sent,MODE)[0]+1:raise RuntimeError('Wardrobe acknowledgement state')
    return dict(zip(('previews','selections','lists','stage'),struct.unpack_from('<4I',reply,RESULT)))

class StoryWardrobe(_Owner):
    def __init__(self,parent,key,*,resources,profile):
        self.profile=decode_profile(encode_profile(profile))
        super().__init__(parent,key,resources=resources)
    def prepare(self):
        if getattr(self.scope._session._transport,'story_wardrobe_protocol',0)!=2:raise RuntimeError('Custom wardrobe requires wardrobe protocol 2')
        if self.started or self.held:raise RuntimeError('Wardrobe preparation is one-shot')
        resources=self.resources
        self.objects=(self.hold(resources.gi),*(self.hold(o) for o in warm(resources,profile=self.profile)))
        self.send(0);self.started=True;return self
    def send(self,mode):
        data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,268,0,0,self.owner)
        for i,obj in enumerate(self.objects):put_id(data,24+i*16,obj.object)
        struct.pack_into('<'+str(COUNT)+'Q',data,LEASES,*(o._token for o in self.objects))
        struct.pack_into('<4I',data,GUID,*(int(self.key[i:i+8],16) for i in range(0,32,8)))
        struct.pack_into('<I',data,MODE,mode);data[PROFILE:TAIL]=encode_profile(self.profile);sent=bytes(data);validate(sent)
        try:
            reply=bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet'])
            self.diagnostics=decode(sent,reply);return self.diagnostics
        except OriginalNarrativeError as error:
            if error.code==4371:self.unknown=True
            raise
        except BaseException:self.unknown=True;raise
    def status(self):return self.send(1)
    def refresh(self):return self.send(3)
    def availability(self,available):
        if type(available) is not bool:raise ValueError("Wardrobe availability must be bool")
        return self.send(5 if available else 4)
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self.send(2);self.started=False
        self.scope.close();self.closed=True;return True
