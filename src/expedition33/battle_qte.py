"""Owned native attack QTE windows and configurable input damage bonus."""
import logging,struct
from .story_original import _Owner
from ._story_original_wire import put_id,identity,OriginalNarrativeError
SIZE=20984
PROFILE=356
TAIL=1676
from ._battle_qte_profile import encode as encode_profile,decode as decode_profile
LOG=logging.getLogger(__name__)
TIMELINE='/Game/Gameplay/Battle/SkillCombos/BP_BattleSequenceTimeline.BP_BattleSequenceTimeline_C:'
METHODS=('DeclareBattleSequenceTimingsAsList','AddQTEPresetKeyframes','GetCurrentTimeForBattleSequenceTimeline','GetCurrentBattleSequenceTimeInAsset','QueueNextBattleSequenceKeyframe')
DAMAGE_METHODS=('/Game/Gameplay/Battle/FL_BattleHelpers.FL_BattleHelpers_C:MakeDamageBuilder',
 '/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Character_Battle_Base.BP_jRPG_Character_Battle_Base_C:GetLastSkillComboInfo')
def warm(resources,*,profile):
 """Load and retain the QTE assets/functions, without installing a hook."""
 config=encode_profile(profile);profile=decode_profile(config)
 resources.scope._check()
 if getattr(resources.scope._session._transport,'battle_qte_protocol',0)!=3:
  raise RuntimeError('Battle combat QTE damage requires protocol 3')
 cache=getattr(resources,'_battle_qte_dependencies',None)
 if cache is None:cache={};resources._battle_qte_dependencies=cache
 previous=cache.get(config)
 if previous is not None:
  if previous['objects'] is None:raise RuntimeError('Incomplete Battle QTE dependency preparation remains owned; restart required')
  if not all(held.active for held in previous['objects']):raise RuntimeError('Battle QTE dependency lease expired')
  return tuple(held.object for held in previous['objects'])
 journal={'objects':None,'error':None}
 cache[config]=journal
 try:
  from .catalog import capture_matching
  sequence=resources.hold(resources.load(profile['sequence']));character=resources.hold(resources.load(profile['character_class'],cls=True))
  catalog=capture_matching(resources.scope.pid,names=METHODS+tuple(p.rsplit(':',1)[1] for p in DAMAGE_METHODS))
  journal['objects']=(sequence,character,*(resources.hold(catalog.find_path(TIMELINE+n)) for n in METHODS),*(resources.hold(catalog.find_path(p)) for p in DAMAGE_METHODS))
  return tuple(held.object for held in journal['objects'])
 except BaseException as error:
  journal['error']=str(error)
  raise

def packet(owner,objects,key,mode=0,*,profile):
 data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,256,0,0,owner)
 if len(objects)!=10:raise ValueError('Ten retained Battle combat inputs required')
 for i,obj in enumerate(objects):put_id(data,24+i*16,obj.object)
 struct.pack_into('<10Q',data,184,*(o._token for o in objects))
 struct.pack_into('<4I',data,264,*(int(key[i:i+8],16) for i in range(0,32,8)))
 struct.pack_into('<I',data,280,mode)
 data[PROFILE:TAIL]=encode_profile(profile)
 result=bytes(data);validate(result);return result
def validate(data):
 if type(data) is not bytes or len(data)!=SIZE or struct.unpack_from('<4I',data)!=(3,256,0,0) or not struct.unpack_from('<Q',data,16)[0]:raise ValueError('Battle combat packet header')
 for at in range(24,184,16):identity(data,at)
 if not all(struct.unpack_from('<10Q',data,184)) or struct.unpack_from('<I',data,264)[0]!=0xe33c5701 or struct.unpack_from('<I',data,280)[0]>2 or any(data[284:PROFILE]) or any(data[TAIL:]):raise ValueError('Battle combat ownership or padding')
 decode_profile(data[PROFILE:TAIL])
def decode(sent,reply):
 validate(sent)
 if type(reply) is not bytes or len(reply)!=SIZE:raise RuntimeError('Battle combat acknowledgement size')
 clean=bytearray(reply);clean[8:16]=sent[8:16];clean[284:356]=sent[284:356]
 if bytes(clean)!=sent:raise RuntimeError('Battle combat acknowledgement context changed')
 error,state=struct.unpack_from('<2I',reply,8)
 if error:raise OriginalNarrativeError(error)
 mode=struct.unpack_from('<I',sent,280)[0]
 if state!=mode+1:raise RuntimeError('Battle combat acknowledgement state')
 return struct.unpack_from('<I',reply,284)[0]
class BattleQTE(_Owner):
 def __init__(self,parent,key,*,resources,profile):
  self.profile=decode_profile(encode_profile(profile));super().__init__(parent,key,resources=resources)
 def send(self,mode):
  sent=packet(self.owner,self.objects,self.key,mode,profile=self.profile)
  try:
   reply=bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet'])
   self.diagnostics=struct.unpack_from('<7I2d',reply,288)
   self.damage_diagnostics=struct.unpack_from('<2I2d',reply,332)
   return decode(sent,reply)
  except OriginalNarrativeError as error:
   if error.code==4251:self.unknown=True
   raise
  except BaseException:self.unknown=True;raise
 def prepare(self):
  if getattr(self.scope._session._transport,'battle_qte_protocol',0)!=3:raise RuntimeError('Battle combat QTE damage requires protocol 3')
  if self.started or self.held:raise RuntimeError('Battle combat preparation is one-shot')
  prepared=warm(self.resources,profile=self.profile)
  self.gi=self.hold(self.resources.gi)
  self.objects=(self.gi,*(self.hold(obj) for obj in prepared))
  self.send(0);self.started=True;return self
 def status(self):
  result=self.send(1)
  if self.diagnostics[6]==11:
   marker=(self.diagnostics[5],self.diagnostics[8])
   if marker!=getattr(self,'_reported_late_qte',None):
    self._reported_late_qte=marker
    LOG.error('Attack QTE timing investigation required: declaration at asset %.6fs left less than the full input interval before impact; no late keys were injected and later casts remain enabled',self.diagnostics[8])
  return result
 def close(self):
  if self.closed:return True
  if self.unknown:return False
  if self.started:self.send(2);self.started=False
  self.scope.close();self.closed=True;return True
