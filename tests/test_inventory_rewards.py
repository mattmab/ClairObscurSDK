import struct,unittest
from types import SimpleNamespace as NS
from expedition33 import inventory_rewards as wire
def held(i):return NS(object=NS(index=i,serial=2,address=0x10000+i*16),_token=i+10)
class InventoryRewardWire(unittest.TestCase):
 def sent(self):return wire.packet(5,held(1),held(2),held(3),'e33c5701000000010000000200000003',item='TestReward')
 def test_save_ownership_and_tail_are_fixed(self):
  sent=self.sent();wire.validate(sent)
  for at in (0,4,96,112,20000):
   changed=bytearray(sent);changed[at]^=1
   with self.assertRaises(ValueError):wire.validate(bytes(changed))
 def test_only_three_authoritative_outcomes(self):
  sent=self.sent()
  for outcome in range(3):
   reply=bytearray(sent);struct.pack_into('<I',reply,12,1);struct.pack_into('<I',reply,112,outcome)
   self.assertEqual(wire.decode(sent,bytes(reply)),('condition-unmet','already-owned','granted')[outcome])
   reply[40]^=1
   with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))

 def test_explicit_reward_selector_is_explicit_and_acknowledgement_cannot_change_it(self):
  sent=wire.packet(5,held(1),held(2),held(3),'e33c5701000000010000000200000003',item='TestReward',quest='TestQuest',objective='TestObjective')
  wire.validate(sent)
  changed=bytearray(sent);struct.pack_into('<I',changed,116,5)
  with self.assertRaises(ValueError):wire.validate(bytes(changed))
  reply=bytearray(sent);struct.pack_into('<I',reply,12,1);struct.pack_into('<I',reply,112,2)
  self.assertEqual(wire.decode(sent,bytes(reply)),'granted')
  struct.pack_into('<I',reply,116,1)
  with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))

 def test_weapon_equip_ack_is_bound_to_exact_character_function_and_save(self):
  sent=wire.packet(5,held(1),held(2),held(3),'e33c5701000000010000000200000003',item='TestWeapon',character='TestGuardian')
  reply=bytearray(sent);struct.pack_into('<I',reply,12,1);struct.pack_into('<I',reply,112,2)
  self.assertEqual(wire.decode(sent,bytes(reply)),'granted')
  for offset in (40,56,96,116):
   wrong=bytearray(reply);wrong[offset]^=1
   with self.assertRaises(RuntimeError):wire.decode(sent,bytes(wrong))

class PreparedWeaponEquipTests(unittest.TestCase):
 def fixture(self):
  from unittest.mock import Mock
  session=NS(_transport=NS(inventory_reward_protocol=2))
  scope=NS(_session=session,pid=17,_check=Mock())
  parent=NS(_session=session,_check=Mock())
  gi=NS(index=1,serial=2,address=0x10010)
  character=NS(index=2,serial=3,address=0x10020,class_index=27)
  function=NS(index=3,serial=4,address=0x10030,pid=17,class_name='Function',
              name='EquipItemInstanceInSlot',outer_index=27,object_flags=0)
  lease=NS(object=function,_token=13,active=True,_scope=lambda:parent,_session=lambda:session)
  resources=NS(scope=parent,gi=gi)
  owner=wire.WeaponEquip.__new__(wire.WeaponEquip)
  owner.scope=scope;owner.resources=resources;owner.held=[];owner.owner=5;owner.unknown=False;owner.closed=False
  owner.key='e33c5701000000010000000200000003'
  owner.hold=Mock(side_effect=lambda obj:NS(object=obj,_token=obj.index+10))
  def command(_,sent):
   reply=bytearray(sent);struct.pack_into('<I',reply,12,1);struct.pack_into('<I',reply,112,2)
   return {'mesh_packet':bytes(reply).hex()}
  session._transport.command=Mock(side_effect=command)
  return owner,character,lease
 def test_prepared_function_eliminates_scan_but_sends_current_actor_and_save_to_original_native_equip(self):
  from contextlib import nullcontext
  from unittest.mock import patch
  owner,character,lease=self.fixture()
  with patch('expedition33.catalog.capture_matching') as scan,patch('expedition33._reader.shared_operation',return_value=nullcontext()):
   owner.prepare(character,character_id='TestGuardian',item='TestWeapon',prepared_function=lease)
  scan.assert_not_called();self.assertIs(owner.function,lease);self.assertEqual(owner.held,[lease])
  self.assertEqual(owner.receipt,'granted')
  self.assertEqual([call.args[0] for call in owner.hold.call_args_list],[owner.resources.gi,character])
  sent=owner.scope._session._transport.command.call_args.args[1]
  self.assertEqual(struct.unpack_from('<iiQ',sent,40),(character.index,character.serial,character.address))
  self.assertEqual(struct.unpack_from('<I',sent,116)[0],2)
 def test_expired_or_foreign_preparation_does_not_fall_back_to_discovery_or_dispatch(self):
  from contextlib import nullcontext
  from unittest.mock import patch
  for changed in ('inactive','scope','session','token','pid','class','name','owner','flags','serial'):
   with self.subTest(changed=changed):
    owner,character,lease=self.fixture()
    if changed=='inactive':lease.active=False
    elif changed=='scope':lease._scope=lambda:object()
    elif changed=='session':lease._session=lambda:object()
    elif changed=='token':lease._token=0
    elif changed=='pid':lease.object.pid=18
    elif changed=='class':lease.object.class_name='Object'
    elif changed=='name':lease.object.name='Other'
    elif changed=='owner':lease.object.outer_index=28
    elif changed=='flags':lease.object.object_flags=0x20
    else:lease.object.serial=0
    with patch('expedition33.catalog.capture_matching') as scan,patch('expedition33._reader.shared_operation',return_value=nullcontext()):
     with self.assertRaises(RuntimeError):owner.prepare(character,character_id='TestGuardian',item='TestWeapon',prepared_function=lease)
    scan.assert_not_called();owner.scope._session._transport.command.assert_not_called()
 def test_legacy_caller_retains_exact_path_discovery(self):
  from contextlib import nullcontext
  from unittest.mock import Mock,patch
  owner,character,lease=self.fixture();catalog=NS(find_path=Mock(return_value=lease.object))
  with patch('expedition33.catalog.capture_matching',return_value=catalog) as scan,patch('expedition33._reader.shared_operation',return_value=nullcontext()):owner.prepare(character,character_id='TestGuardian',item='TestWeapon')
  scan.assert_called_once_with(17,names=('EquipItemInstanceInSlot',))
  catalog.find_path.assert_called_once_with(wire.EQUIP_ITEM)
  self.assertEqual(owner.receipt,'granted')
 def test_prepared_function_cannot_mask_unknown_native_result(self):
  from contextlib import nullcontext
  from unittest.mock import patch
  owner,character,lease=self.fixture()
  owner.scope._session._transport.command.side_effect=RuntimeError('lost ACK')
  with patch('expedition33.catalog.capture_matching') as scan,patch('expedition33._reader.shared_operation',return_value=nullcontext()):
   with self.assertRaisesRegex(RuntimeError,'lost ACK'):owner.prepare(character,character_id='TestGuardian',item='TestWeapon',prepared_function=lease)
  scan.assert_not_called();self.assertTrue(owner.unknown);self.assertFalse(owner.close())
  self.assertEqual(owner.held,[lease]);owner.scope._session._transport.command.assert_called_once()

class InventoryRewardContextTests(unittest.TestCase):
 key='e33c5701000000010000000200000003'
 visit=(20,3,0x20000)
 def fixture(self):
  from unittest.mock import Mock
  def command(_,sent):
   reply=bytearray(sent);struct.pack_into('<I',reply,12,1);struct.pack_into('<I',reply,112,1)
   return {'mesh_packet':bytes(reply).hex()}
  session=NS(_transport=NS(command=Mock(side_effect=command),inventory_reward_protocol=2))
  parent=NS(_session=session,pid=17,_check=Mock())
  gi=NS(index=1,serial=2,address=0x10010)
  manager=NS(index=2,serial=2,address=0x10020,class_name=wire.MANAGER,object_flags=0)
  function=NS(index=3,serial=2,address=0x10030)
  resources=NS(scope=parent,gi=gi)
  leases={obj.index:NS(object=obj,_token=obj.index+10,active=True) for obj in (gi,manager,function)}
  def owner():
   value=wire.InventoryReward.__new__(wire.InventoryReward)
   value._scope=parent;value.scope=NS(_session=session,pid=17);value.resources=resources;value.key=self.key
   value.owner=5;value.closed=False;value.unknown=False;value.hold=Mock(side_effect=lambda obj:leases[obj.index])
   return value
  catalog=NS(objects=(manager,),find_path=Mock(return_value=function))
  def observed(reference=gi,current=manager,errors=None,truncated=frozenset()):
   key=(50,'GameInstanceReference')
   values=NS(values={key:reference},types={key:'ObjectProperty'},errors=errors or {},truncated=truncated)
   return NS(by_index={manager.index:current}),{manager.index:values}
  context=wire.InventoryRewardContext(parent,self.key,self.visit,resources=resources)
  return context,owner,catalog,observed,leases
 def test_two_rewards_scan_once_but_reobserve_exact_manager_and_gi_each_time(self):
  from contextlib import nullcontext
  from unittest.mock import patch
  context,owner,catalog,observed,_=self.fixture()
  with patch('expedition33.catalog.capture_matching',return_value=catalog) as scan,patch('expedition33.values.capture_selected_values',side_effect=lambda *a,**kw:observed()) as read,patch('expedition33._reader.shared_operation',return_value=nullcontext()):
   first=owner();second=owner()
   first.prepare('TestRewardA',inventory_context=context,world=self.visit)
   second.prepare('TestRewardB',inventory_context=context,world=self.visit)
  self.assertEqual(first.receipt,'already-owned');self.assertEqual(second.receipt,'already-owned')
  scan.assert_called_once();self.assertEqual(read.call_count,2)
  self.assertEqual([call.args for call in read.call_args_list],[(17,((2,2,0x10020),))]*2)
  sent=context.session._transport.command.call_args_list
  self.assertEqual([call.args[1][120:216].split(b'\0',1)[0] for call in sent],[b'TestRewardA',b'TestRewardB'])
 def test_context_rejects_scope_session_key_world_changes_before_any_read_or_reward(self):
  from unittest.mock import Mock,patch
  for changed in ('scope','session','key','world','resources'):
   with self.subTest(changed=changed):
    context,owner,_,_,_=self.fixture();value=owner();world=self.visit
    if changed=='scope':value._scope=object()
    elif changed=='session':value.scope._session=object()
    elif changed=='key':value.key='e33c5701000000010000000200000004'
    elif changed=='world':world=(21,3,0x20000)
    elif changed=='resources':value.resources=object()
    with patch('expedition33.catalog.capture_matching') as scan,patch('expedition33.values.capture_selected_values') as read:
     with self.assertRaisesRegex(RuntimeError,'another scope, save or world'):context.acquire(value,world)
    scan.assert_not_called();read.assert_not_called();context.session._transport.command.assert_not_called()
 def test_changed_manager_identity_or_gi_never_falls_back_to_rescan(self):
  from unittest.mock import patch
  for changed in ('gi','manager','truncated','errors'):
   with self.subTest(changed=changed):
    context,owner,catalog,observed,leases=self.fixture()
    with patch('expedition33.catalog.capture_matching',return_value=catalog) as scan,patch('expedition33.values.capture_selected_values',return_value=observed()) as read:
     context.acquire(owner(),self.visit)
     if changed=='gi':read.return_value=observed(reference=NS(index=1,serial=99,address=0x10010))
     elif changed=='manager':read.return_value=observed(current=NS(index=2,serial=99,address=0x10020,class_name=wire.MANAGER,object_flags=0))
     elif changed=='truncated':read.return_value=observed(truncated=frozenset({(50,'GameInstanceReference')}))
     else:read.return_value=observed(errors={(50,'GameInstanceReference'):'unreadable'})
     with self.assertRaises(RuntimeError):context.acquire(owner(),self.visit)
     with self.assertRaisesRegex(RuntimeError,'unavailable'):context.acquire(owner(),self.visit)
    scan.assert_called_once();self.assertEqual(read.call_count,2)
    context.session._transport.command.assert_not_called()
 def test_native_unknown_outcome_poison_context_and_cannot_be_replayed_by_another_owner(self):
  from contextlib import nullcontext
  from unittest.mock import patch
  context,owner,catalog,observed,_=self.fixture()
  context.session._transport.command.side_effect=RuntimeError('lost acknowledgement')
  value=owner()
  with patch('expedition33.catalog.capture_matching',return_value=catalog),patch('expedition33.values.capture_selected_values',return_value=observed()),patch('expedition33._reader.shared_operation',return_value=nullcontext()):
   with self.assertRaisesRegex(RuntimeError,'lost acknowledgement'):value.prepare('TestRewardA',inventory_context=context,world=self.visit)
   self.assertTrue(value.unknown)
   with self.assertRaisesRegex(RuntimeError,'unavailable'):owner().prepare('TestRewardB',inventory_context=context,world=self.visit)
  context.session._transport.command.assert_called_once()
 def test_closed_scope_or_expired_lease_cannot_be_reused(self):
  from unittest.mock import patch
  context,owner,catalog,observed,leases=self.fixture()
  with patch('expedition33.catalog.capture_matching',return_value=catalog),patch('expedition33.values.capture_selected_values',return_value=observed()):context.acquire(owner(),self.visit)
  leases[2].active=False
  with self.assertRaisesRegex(RuntimeError,'ownership changed'):context.acquire(owner(),self.visit)
  context,owner,_,_,_=self.fixture();context.scope._check.side_effect=RuntimeError('scope closed')
  with self.assertRaisesRegex(RuntimeError,'scope closed'):context.acquire(owner(),self.visit)
  context.session._transport.command.assert_not_called()
 def test_initial_reference_is_exact_not_address_only(self):
  from unittest.mock import patch
  context,owner,catalog,observed,_=self.fixture()
  with patch('expedition33.catalog.capture_matching',return_value=catalog),patch('expedition33.values.capture_selected_values',return_value=observed(reference=NS(index=1,serial=99,address=0x10010))):
   with self.assertRaisesRegex(RuntimeError,'exact selected-save'):context.acquire(owner(),self.visit)
  self.assertIsNone(context.inputs);context.session._transport.command.assert_not_called()
 def test_reward_owner_is_one_shot_even_after_acknowledgement(self):
  from contextlib import nullcontext
  from unittest.mock import patch
  context,owner,catalog,observed,_=self.fixture();value=owner()
  with patch('expedition33.catalog.capture_matching',return_value=catalog),patch('expedition33.values.capture_selected_values',return_value=observed()),patch('expedition33._reader.shared_operation',return_value=nullcontext()):
   value.prepare('TestRewardA',inventory_context=context,world=self.visit)
   with self.assertRaisesRegex(RuntimeError,'new reward owner'):value.prepare('TestRewardA',inventory_context=context,world=self.visit)
  context.session._transport.command.assert_called_once()
