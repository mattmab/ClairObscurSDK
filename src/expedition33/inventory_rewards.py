"""Save-scoped unique inventory rewards and equipping into an empty weapon slot."""
import re,struct
from .story_original import _Owner
from ._story_original_wire import identity,put_id,OriginalNarrativeError
SIZE=20984
MANAGER='AC_jRPG_InventoryManager_C'
ADD_ITEM='/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_InventoryManager.AC_jRPG_InventoryManager_C:AddItemToInventory'
EQUIP_ITEM='/Game/Gameplay/CharacterData/BP_CharacterData.BP_CharacterData_C:EquipItemInstanceInSlot'

class InventoryRewardContext:
 """One selected-save preparation visit, with fresh manager/GI proof per reward.

 This caches only leased input identities. It never caches inventory contents,
 reward outcomes or native save admission, and it cannot cross owner scopes.
 """
 def __init__(self,parent,key,world,*,resources):
  parent._check()
  if type(key)is not str or len(key)!=32:raise ValueError('Inventory reward save identity required')
  visit=tuple(world)
  if len(visit)!=3 or any(type(v)is not int for v in visit):raise ValueError('Inventory reward world visit identity required')
  if resources.scope._session is not parent._session:raise ValueError('Inventory resources belong to another session')
  self.scope=parent;self.session=parent._session;self.key=key;self.world=visit;self.resources=resources
  self.inputs=None;self.error=None;self.closed=False
 def _reference(self,value):
  from .story_dialogue import field
  if value.errors or value.truncated:raise RuntimeError('Inventory manager observation is incomplete')
  return field(value,'GameInstanceReference')
 def acquire(self,owner,world):
  from .catalog import capture_matching
  from .values import capture_selected_values
  from .story_dialogue import identity as object_identity
  self.scope._check()
  if self.closed or self.error is not None:raise RuntimeError('Inventory reward preparation context is unavailable')
  try:
   if (owner._scope is not self.scope or owner.scope._session is not self.session or owner.key!=self.key or
       owner.resources is not self.resources or tuple(world)!=self.world):
    raise RuntimeError('Inventory reward context belongs to another scope, save or world')
   if self.inputs is None:
    gi=owner.hold(self.resources.gi)
    catalog=capture_matching(self.scope.pid,classes=(MANAGER,),names=('AddItemToInventory',))
    candidates=tuple(obj for obj in catalog.objects if obj.class_name==MANAGER and not obj.object_flags&0x30)
    if not 1<=len(candidates)<=32:raise RuntimeError('Inventory manager discovery is missing or exceeds its bound')
    fresh,values=capture_selected_values(self.scope.pid,tuple(object_identity(obj) for obj in candidates),fields=('GameInstanceReference',),references=True)
    selected=[fresh.by_index[obj.index] for obj in candidates if object_identity(self._reference(values[obj.index]))==object_identity(gi.object)]
    if len(selected)!=1:raise RuntimeError('One exact selected-save inventory manager required')
    manager=selected[0]
    if manager.class_name!=MANAGER or manager.object_flags&0x30:raise RuntimeError('Inventory manager class or lifetime changed')
    self.inputs=(gi,owner.hold(manager),owner.hold(catalog.find_path(ADD_ITEM)))
   else:
    gi,manager,function=self.inputs
    if not all(held.active for held in self.inputs) or object_identity(self.resources.gi)!=object_identity(gi.object):
     raise RuntimeError('Inventory reward input ownership changed')
    fresh,values=capture_selected_values(self.scope.pid,(object_identity(manager.object),),fields=('GameInstanceReference',),references=True)
    current=fresh.by_index[manager.object.index]
    if (object_identity(current)!=object_identity(manager.object) or current.class_name!=MANAGER or current.object_flags&0x30 or
        object_identity(self._reference(values[current.index]))!=object_identity(gi.object)):
     raise RuntimeError('Inventory manager no longer belongs to the exact prepared game instance')
   return tuple(owner.hold(held.object) for held in self.inputs)
  except BaseException as error:
   self.error=str(error);raise
 def close(self):
  # Narrative resources retain shared process inputs. No gameplay owner is
  # installed here and this context never closes its caller's parent scope.
  self.closed=True
def reward_fields(*,item,quest='',objective='',character=''):
 values=(item,character,quest,objective)
 for i,value in enumerate(values):
  if type(value)is not str or (not value and i==0) or (value and re.fullmatch(r'[A-Za-z0-9_]{1,95}',value) is None):
   raise ValueError('Reward IDs must be bounded ASCII identifiers')
 if bool(quest)!=bool(objective) or (character and quest):raise ValueError('Reward condition and equip target conflict')
 mode=2 if character else 0 if quest else 1
 return mode,values

def packet(owner,gi,manager,function,key,*,item,quest='',objective='',character=''):
 mode,values=reward_fields(item=item,quest=quest,objective=objective,character=character)
 data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,253,0,0,owner)
 for at,held in ((24,gi),(40,manager),(56,function)):put_id(data,at,held.object)
 struct.pack_into('<3Q',data,72,gi._token,manager._token,function._token)
 if type(key)is not str or len(key)!=32:raise ValueError('Selected story key required')
 struct.pack_into('<4I',data,96,*(int(key[i:i+8],16) for i in range(0,32,8)))
 struct.pack_into('<I',data,116,mode)
 for i,value in enumerate(values):data[120+i*96:216+i*96]=value.encode('ascii').ljust(96,b'\0')
 result=bytes(data);validate(result);return result

def validate(data):
 if type(data)is not bytes or len(data)!=SIZE:raise ValueError('Inventory reward packet size')
 if struct.unpack_from('<4I',data)!=(3,253,0,0) or not struct.unpack_from('<Q',data,16)[0]:raise ValueError('Inventory reward header')
 for at in (24,40,56):identity(data,at)
 if not all(struct.unpack_from('<3Q',data,72)) or struct.unpack_from('<I',data,96)[0]!=0xe33c5701 or any(data[112:116]) or any(data[504:]):
  raise ValueError('Inventory reward selected save or padding')
 values=[]
 for i in range(4):
  raw=data[120+i*96:216+i*96];value=raw.split(b'\0',1)[0]
  if raw!=value.ljust(96,b'\0') or len(value)==96:raise ValueError('Inventory reward ID padding')
  values.append(value.decode('ascii'))
 mode,_=reward_fields(item=values[0],character=values[1],quest=values[2],objective=values[3])
 if struct.unpack_from('<I',data,116)[0]!=mode:raise ValueError('Inventory reward mode differs from its explicit inputs')

def decode(sent,reply):
 validate(sent)
 if type(reply) is not bytes or len(reply)!=SIZE:raise RuntimeError('Inventory reward acknowledgement size')
 clean=bytearray(reply);clean[8:16]=sent[8:16];clean[112:116]=sent[112:116]
 if bytes(clean)!=sent:raise RuntimeError('Inventory reward acknowledgement changed context')
 error,state=struct.unpack_from('<2I',reply,8)
 if error:raise OriginalNarrativeError(error)
 outcome=struct.unpack_from('<I',reply,112)[0]
 if state!=1 or outcome>2:raise RuntimeError('Inventory reward acknowledgement state')
 return ('condition-unmet','already-owned','granted')[outcome]
class InventoryReward(_Owner):
 def prepare(self,item,*,quest='',objective='',inventory_context=None,world=None):
  reward_fields(item=item,quest=quest,objective=objective)
  if getattr(self.scope._session._transport,'inventory_reward_protocol',0)!=2:raise RuntimeError('Inventory rewards require protocol 2')
  if self.closed or self.unknown or getattr(self,'_prepared_inventory_reward',False):raise RuntimeError('Inventory rewards require a new reward owner')
  from .catalog import capture_matching
  from ._reader import shared_operation
  with shared_operation(self.scope.pid):
   if inventory_context is not None:
    self.gi,self.manager,self.function=inventory_context.acquire(self,world)
   else:
    if self.resources is not None:self.gi=self.hold(self.resources.gi)
    else:self.context()
    c=capture_matching(self.scope.pid,classes=(MANAGER,),names=('AddItemToInventory',))
    from .values import read_values_with_references
    managers=[]
    for o in c.objects:
     if o.class_name!=MANAGER or o.object_flags&0x30:continue
     v,_=read_values_with_references(c,o,fields=('GameInstanceReference',))
     refs=[x for k,x in v.values.items() if k[1]=='GameInstanceReference']
     if len(refs)==1 and refs[0] is not None and refs[0].address==self.gi.object.address:managers.append(o)
    if len(managers)!=1:raise RuntimeError('One selected-save inventory manager required')
    self.manager=self.hold(managers[0]);self.function=self.hold(c.find_path(ADD_ITEM))
   sent=packet(self.owner,self.gi,self.manager,self.function,self.key,item=item,quest=quest,objective=objective)
   try:
    self._prepared_inventory_reward=True
    self.receipt=decode(sent,bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet']))
   except OriginalNarrativeError as error:
    if inventory_context is not None:inventory_context.error=str(error)
    if error.code==4231:self.unknown=True
    raise
   except BaseException as error:
    if inventory_context is not None:inventory_context.error=str(error)
    self.unknown=True;raise
  return self
 def close(self):
  if self.unknown:return False
  if not self.closed:self.scope.close();self.closed=True
  return True

class WeaponEquip(_Owner):
 """Equip an owned weapon into an explicitly named character's empty slot."""
 def _prepared_function(self,character,lease):
  # Borrow only an existing process-owned immutable function. Its owner must
  # outlive this adapter; no dynamic CharacterData or save state is cached.
  resources=self.resources
  if resources is None:raise RuntimeError('Prepared weapon equip function requires narrative resources')
  resources.scope._check();self.scope._check()
  if (resources.scope._session is not self.scope._session or lease.active is not True or
      lease._scope is None or lease._scope() is not resources.scope or
      lease._session() is not self.scope._session or not lease._token):
   raise RuntimeError('Prepared weapon equip function ownership changed')
  function=lease.object
  if (function.pid!=self.scope.pid or function.class_name!='Function' or
      function.name!='EquipItemInstanceInSlot' or function.outer_index!=character.class_index or
      function.object_flags&0x30 or function.serial<=0):
   raise RuntimeError('Prepared weapon equip function is not the exact character method')
  self.held.append(lease)
  return lease
 def prepare(self,character,*,character_id,item,prepared_function=None):
  reward_fields(item=item,character=character_id)
  if getattr(self.scope._session._transport,'inventory_reward_protocol',0)!=2:
   raise RuntimeError('Weapon equip requires inventory reward protocol 2')
  if self.closed or self.unknown or getattr(self,'_prepared_inventory_reward',False):raise RuntimeError('Weapon equip requires a new reward owner')
  from .catalog import capture_matching
  from ._reader import shared_operation
  with shared_operation(self.scope.pid):
   if self.resources is not None:self.gi=self.hold(self.resources.gi)
   else:self.context()
   if prepared_function is None:
    c=capture_matching(self.scope.pid,names=('EquipItemInstanceInSlot',))
    self.function=self.hold(c.find_path(EQUIP_ITEM))
   else:self.function=self._prepared_function(character,prepared_function)
   self.manager=self.hold(character)
   sent=packet(self.owner,self.gi,self.manager,self.function,self.key,item=item,character=character_id)
   self._prepared_inventory_reward=True
   try:self.receipt=decode(sent,bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet']))
   except OriginalNarrativeError as error:
    if error.code==4231:self.unknown=True
    raise
   except BaseException:self.unknown=True;raise
  return self
 def close(self):
  if self.unknown:return False
  if not self.closed:self.scope.close();self.closed=True
  return True
