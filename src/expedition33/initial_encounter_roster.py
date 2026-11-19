"""Owned complete initial roster for the original enemy-spawn/initiative pass."""
import re,struct
from ._scope import SessionScope
from ._stable_lease import acquire_stable
from ._story_original_wire import identity,put_id
SIZE=20984
PREFIX='/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C:'
ENEMY_TABLE='/Game/jRPGTemplate/Datatables/DT_jRPG_Enemies.DT_jRPG_Enemies'
METADATA=(PREFIX+'SpawnEnemies','/Script/Engine.BlueprintMapLibrary:Map_Add')

def warm(resources):
 """Retain immutable roster inputs without touching a live battle or table."""
 resources.scope._check()
 journal=getattr(resources,'_initial_roster_inputs',None)
 if journal is not None:
  if not journal['ready']:raise RuntimeError('Initial roster input preparation failed; not replayed')
  if not all(held.active for held in journal['objects']):raise RuntimeError('Initial roster dependency lease expired')
  return tuple(held.object for held in journal['objects'])
 from .catalog import capture_matching
 journal=dict(ready=False,objects=[]);resources._initial_roster_inputs=journal
 catalog=capture_matching(resources.scope.pid,names=('SpawnEnemies','Map_Add'))
 for path in METADATA:journal['objects'].append(resources.hold(catalog.find_path(path)))
 journal['objects'].append(resources.hold(resources.load(ENEMY_TABLE)))
 journal['ready']=True
 return tuple(held.object for held in journal['objects'])

def validate(data):
 if type(data)is not bytes or len(data)!=SIZE:raise ValueError('Initial roster packet size')
 version,op,error,state,owner=struct.unpack_from('<4IQ',data)
 if (version,op,error,state)!=(3,257,0,0) or not owner:raise ValueError('Initial roster header')
 for at in range(24,136,16):identity(data,at)
 if not all(struct.unpack_from('<7Q',data,136)):raise ValueError('Initial roster leases')
 mode,count=struct.unpack_from('<2I',data,192)
 if mode>2 or not 1<=count<=10 or any(data[1160:]):raise ValueError('Initial roster mode/count/padding')
 for i in range(10):
  value,padding=data[200+i*96:296+i*96].split(b'\0',1) if b'\0' in data[200+i*96:296+i*96] else (b'',b'X')
  if any(padding) or (i<count and re.fullmatch(rb'[A-Za-z0-9_]{1,95}',value)is None) or (i>=count and value):raise ValueError('Initial roster definition')

def packet(owner,objects,names,mode=0):
 if len(objects)!=7:raise ValueError('Seven initial roster dependencies required')
 data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,257,0,0,owner)
 for i,obj in enumerate(objects):put_id(data,24+i*16,obj.object)
 struct.pack_into('<7Q',data,136,*(o._token for o in objects));struct.pack_into('<2I',data,192,mode,len(names))
 for i,name in enumerate(names):
  if type(name)is not str or re.fullmatch('[A-Za-z0-9_]{1,95}',name)is None:raise ValueError('Initial roster definition')
  data[200+i*96:200+i*96+len(name)]=name.encode('ascii')
 result=bytes(data);validate(result);return result

def decode(sent,reply):
 validate(sent)
 if type(reply)is not bytes or len(reply)!=SIZE:raise RuntimeError('Initial roster acknowledgement size')
 copy=bytearray(reply);copy[8:16]=sent[8:16];copy[1160:1164]=sent[1160:1164]
 if bytes(copy)!=sent:raise RuntimeError('Initial roster acknowledgement changed context')
 error,state=struct.unpack_from('<2I',reply,8)
 if error:raise RuntimeError(f'Initial roster native error {error}; owner retained')
 if state!=struct.unpack_from('<I',sent,192)[0]+1:raise RuntimeError('Initial roster acknowledgement state')
 return struct.unpack_from('<I',reply,1160)[0]

class InitialEncounterRoster:
 def __init__(self,parent,enemy_owner):
  parent._check()
  if getattr(parent._session._transport,'initial_encounter_roster_protocol',0)!=1:raise RuntimeError('Updated native initial-roster capability required')
  self._scope=parent;self.scope=SessionScope(parent);self.enemy=enemy_owner;self.owner=enemy_owner._owner
  self.objects=[];self.names=();self.started=False;self.closed=False;self.unknown=False
  parent._register_native_owner(self);parent._close_before_descendants(self)
 @property
 def state(self):return 'closed' if self.closed else 'unknown' if self.unknown else 'active'
 def hold(self,obj):
  held,_=acquire_stable(self.scope,obj);self.objects.append(held);return held
 def prepare(self,names,*,resources=None,observe_context=None):
  if self.started or self.objects:raise RuntimeError('Initial roster is one-shot')
  names=tuple(names)
  if not 1<=len(names)<=10 or any(type(n)is not str or re.fullmatch('[A-Za-z0-9_]{1,95}',n)is None for n in names):raise ValueError('One to ten enemy definitions required')
  from .catalog import capture_matching,capture_selected
  from .cinematics.controller_anchor import context_observer
  from ._npc_encounter_preparation import _controller_battle_manager
  from .assets import load_asset
  from ._reader import shared_operation
  if resources is not None and resources.scope._session is not self.scope._session:
   raise RuntimeError('Initial roster resources belong to another session')
  with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
   observe=observe_context if observe_context is not None else context_observer(self.scope)
   context=observe()
   inputs=warm(resources) if resources is not None else None
   selected=(tuple(self.enemy.actor_identity),context['world'][1:],context['controller'][1:])
   if inputs is not None:
    selected+=tuple((obj.index,obj.serial,obj.address) for obj in inputs)
    c=capture_selected(self.scope.pid,selected)
   else:
    c=capture_matching(self.scope.pid,names=('SpawnEnemies','Map_Add'))
    c=c.with_observations(capture_selected(self.scope.pid,selected))
   actor=c.by_index[self.enemy.actor_identity[0]];world=c.by_index[context['world'][1]];pc=c.by_index[context['controller'][1]]
   manager,c=_controller_battle_manager(c,pc)
   first=(actor,world,pc,manager,c.find_path(PREFIX+'SpawnEnemies'))
   map_add=c.find_path('/Script/Engine.BlueprintMapLibrary:Map_Add')
   if observe()!=context:raise RuntimeError('World/controller changed during initial roster preparation')
  for obj in first:self.hold(obj)
  if inputs is not None:self.hold(c.find_path(ENEMY_TABLE))
  else:
   table=load_asset(self.scope,ENEMY_TABLE)
   self.hold(table.return_value);table.release()
  self.hold(map_add)
  self.names=names;self.send(0);self.started=True;return self
 def send(self,mode):
  sent=packet(self.owner,self.objects,self.names,mode)
  try:
   reply=bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet'])
   return decode(sent,reply)
  except BaseException:self.unknown=True;raise
 def status(self):return self.send(1)
 def close(self):
  if self.closed:return True
  if self.unknown:return False
  if self.started:self.send(2);self.started=False
  self.scope.close();self.closed=True;return True
