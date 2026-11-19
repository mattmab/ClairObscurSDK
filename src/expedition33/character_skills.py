"""Save-owned synchronous skill effects, sequence selection and meter rules.

Game APIs still own damage, buffs, healing, animations and turn scheduling.
The authored skill decisions execute in the SDK game-thread owner.
"""
import math,struct
from .story_original import _Owner
from ._story_original_wire import put_id,identity,OriginalNarrativeError
from ._character_skill_schema import INPUTS,ROLES
from ._character_skill_config import encode as encode_profile,decode as decode_profile,inputs as profile_inputs,active
SIZE=20984
COUNT=len(INPUTS)
LEASES=24+16*COUNT
GUID=LEASES+8*COUNT
MODE=GUID+16
RESULT=MODE+4
DIAGNOSTICS=124
PROFILE=RESULT+DIAGNOSTICS
TAIL=PROFILE+16276

def warm(resources,*,profile):
 """Retain immutable dependencies, without a game instance or save hooks.

 Each save owner still supplies the current GI and all live identities/leases
 to native validation. A partial warm remains owned and is never replayed.
 """
 config=encode_profile(profile);profile=decode_profile(config);inputs=profile_inputs(profile)
 resources.scope._check()
 if getattr(resources.scope._session._transport,'character_skills_protocol',0)!=3:
  raise RuntimeError('Character skills require SDK native skill ownership protocol 3')
 cache=getattr(resources,'_character_skill_dependencies',None)
 if cache is None:cache={};resources._character_skill_dependencies=cache
 previous=cache.get(config)
 if previous is not None:
  if previous['objects'] is None:raise RuntimeError('Incomplete Character skill dependency preparation remains owned; restart required')
  if not all(held.active for held in previous['objects'][1:] if held is not None):raise RuntimeError('Character skill dependency lease expired')
  return tuple(held.object if held is not None else None for held in previous['objects'])
 journal={'objects':None,'error':None}
 cache[config]=journal
 try:
  from .catalog import capture_matching
  resolved={i:None for i in range(COUNT)}
  for i,spec in enumerate(inputs):
   if spec is not None and spec['kind'] in ('class','asset'):
    resolved[i]=resources.hold(resources.load(spec['path'],cls=spec['kind']=='class'))
  names=tuple(sorted({s['path'].rsplit(':',1)[-1] if s['kind']=='function' else s['path'].rsplit('.',1)[-1] for s in inputs if s is not None and s['kind']in('function','cdo')}))
  catalog=capture_matching(resources.scope.pid,names=names)
  for i,spec in enumerate(inputs):
   if spec is not None and spec['kind']in('function','cdo'):resolved[i]=resources.hold(catalog.find_path(spec['path']))
  journal['objects']=tuple(resolved[i] for i in range(COUNT))
  return tuple(held.object if held is not None else None for held in journal['objects'])
 except BaseException as error:
  journal['error']=str(error)
  raise

def packet(owner,objects,key,mode=0,*,profile):
 profile=decode_profile(encode_profile(profile))
 if len(objects)!=COUNT:raise ValueError('All reviewed Character skill dependencies are required')
 if type(key)is not str or len(key)!=32:raise ValueError('Character skill save identity')
 data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,259,0,0,owner)
 for i,obj in enumerate(objects):
  if obj is not None:put_id(data,24+i*16,obj.object)
 struct.pack_into('<'+str(COUNT)+'Q',data,LEASES,*(o._token if o is not None else 0 for o in objects))
 struct.pack_into('<4I',data,GUID,*(int(key[i:i+8],16) for i in range(0,32,8)))
 struct.pack_into('<I',data,MODE,mode)
 data[PROFILE:TAIL]=encode_profile(profile)
 result=bytes(data);validate(result);return result

def validate(data):
 if type(data)is not bytes or len(data)!=SIZE or struct.unpack_from('<4I',data)!=(3,259,0,0) or not struct.unpack_from('<Q',data,16)[0]:raise ValueError('Character skill packet header')
 profile=decode_profile(data[PROFILE:TAIL]);tokens=struct.unpack_from('<'+str(COUNT)+'Q',data,LEASES)
 for i in range(COUNT):
  at=24+i*16
  if active(i,len(profile['skills']),profile['meter']['enabled']):
   identity(data,at)
   if not tokens[i]:raise ValueError('Missing active skill lease')
  elif any(data[at:at+16]) or tokens[i]:raise ValueError('Inactive skill input must be empty')
 if struct.unpack_from('<I',data,GUID)[0]!=0xe33c5701 or struct.unpack_from('<I',data,MODE)[0]>2 or any(data[RESULT:PROFILE]) or any(data[TAIL:]):raise ValueError('Character skill ownership/padding')

def decode(sent,reply):
 validate(sent)
 if type(reply)is not bytes or len(reply)!=SIZE:raise RuntimeError('Character skill acknowledgement size')
 clean=bytearray(reply);clean[8:16]=sent[8:16];clean[RESULT:RESULT+DIAGNOSTICS]=sent[RESULT:RESULT+DIAGNOSTICS]
 if bytes(clean)!=sent:raise RuntimeError('Character skill acknowledgement context changed')
 error,state=struct.unpack_from('<2I',reply,8)
 if error:
  failure=OriginalNarrativeError(error)
  failure.stage=struct.unpack_from("<I",reply,RESULT+92)[0]
  failure.add_note("Character skill native stage: "+str(failure.stage))
  raise failure
 if state!=struct.unpack_from('<I',sent,MODE)[0]+1:raise RuntimeError('Character skill acknowledgement state')
 values=struct.unpack_from('<24I2d3I',reply,RESULT)
 if not all(math.isfinite(v) and 0<=v<=1e6 for v in values[24:26]):raise RuntimeError('Character skill diagnostic values')
 return dict(executions=values[:9],effects=values[9:18],damage_hits=values[18],buffs=values[19],heals=values[20],
             meter_hits=values[21],meter_procs=values[22],stage=values[23],last_damage_factor=values[24],last_qte_multiplier=values[25],
             meter_starts=values[26],meter_initialized=values[27],meter_forwarded=values[28])

class CharacterSkills(_Owner):
 def __init__(self,parent,key,*,resources,profile):
  self.profile=decode_profile(encode_profile(profile));super().__init__(parent,key,resources=resources)
 def send(self,mode):
  sent=packet(self.owner,self.objects,self.key,mode,profile=self.profile)
  try:
   reply=bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet'])
   self.diagnostics=decode(sent,reply);return self.diagnostics
  except OriginalNarrativeError as error:
   if error.code==4281:self.unknown=True
   raise
  except BaseException:self.unknown=True;raise
 def prepare(self):
  if getattr(self.scope._session._transport,'character_skills_protocol',0)!=3:raise RuntimeError('Character skills require SDK native skill ownership protocol 3')
  if self.started or self.held:raise RuntimeError('Character skill preparation is one-shot')
  prepared=warm(self.resources,profile=self.profile)
  self.objects=(self.hold(self.resources.gi),*(self.hold(obj) if obj is not None else None for obj in prepared[1:]))
  self.send(0);self.started=True;return self
 def status(self):return self.send(1)
 def close(self):
  if self.closed:return True
  if self.unknown:return False
  if self.started:self.send(2);self.started=False
  self.scope.close();self.closed=True;return True
