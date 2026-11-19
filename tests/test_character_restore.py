import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.character_restore import packet as _packet,validate,decode,CharacterRestore
from expedition33._story_original_wire import OriginalNarrativeError

PROFILE=dict(character='TestScholar',graph='/Game/SDK/Sample/Graph.Graph',skills=tuple(dict(id=f'Skill{i}',asset=f'/Game/SDK/Sample/Skill{i}.Skill{i}',unlock_cost=i) for i in range(9)))
def packet(*args,**kwargs):
 kwargs.setdefault('profile',PROFILE);return _packet(*args,**kwargs)

class RestoreWireTests(unittest.TestCase):
 def inputs(self):return [N(object=N(index=i+1,serial=2,address=0x10000+16*i),_token=10+i) for i in range(10)]
 def sent(self,mode=0):return packet(42,self.inputs(),'e33c5701000000010000000200000003',mode)
 def test_protocol_five_binds_both_cosmetic_callbacks_and_rejects_old_wire(self):
  sent=self.sent()
  self.assertEqual(struct.unpack_from('<2I',sent),(5,261))
  self.assertEqual(struct.unpack_from('<10Q',sent,184),tuple(range(10,20)))
  self.assertEqual(struct.unpack_from('<4I',sent,264),(0xe33c5701,1,2,3))
  for version in (1,2,3,4):
   old=bytearray(sent);struct.pack_into('<I',old,0,version)
   with self.assertRaises(ValueError):validate(bytes(old))
  with self.assertRaisesRegex(ValueError,'Ten exact'):packet(42,self.inputs()[:8],'e33c5701000000010000000200000003')
 def reply(self,sent,mode=0):
  reply=bytearray(sent);struct.pack_into('<I',reply,12,mode+1)
  if mode!=2:struct.pack_into('<4I',reply,284,20,1,7,6)
  return bytes(reply)
 def test_saved_and_live_graph_sources_have_exact_receipts(self):
  sent=self.sent();self.assertEqual(decode(sent,self.reply(sent)),dict(stage=20,source='saved-state',unlocked=7,equipped=6))
  reply=bytearray(self.reply(sent));struct.pack_into('<I',reply,288,2)
  self.assertEqual(decode(sent,bytes(reply))['source'],'live-graph')
 def test_entire_identity_lease_and_selected_save_are_correlated(self):
  sent=self.sent()
  for offset in (*range(24,184,16),*range(184,264,8),264,268,272,276,280,300,20983):
   reply=bytearray(self.reply(sent));reply[offset]^=1
   with self.assertRaisesRegex(RuntimeError,'context changed'):decode(sent,bytes(reply))
 def test_invalid_counts_or_unfinished_native_stage_are_not_success(self):
  sent=self.sent()
  for at,value in ((284,11),(288,0),(288,3),(292,0),(292,10),(296,7)):
   reply=bytearray(self.reply(sent));struct.pack_into('<I',reply,at,value)
   with self.assertRaisesRegex(RuntimeError,'incomplete'):decode(sent,bytes(reply))
 def test_status_and_close_are_distinct(self):
  for mode in (1,2):
   sent=self.sent(mode);decode(sent,self.reply(sent,mode))
   reply=bytearray(self.reply(sent,mode));struct.pack_into('<I',reply,12,1)
   with self.assertRaisesRegex(RuntimeError,'state'):decode(sent,bytes(reply))
 def test_client_cannot_submit_a_skill_array_or_nonzero_diagnostics(self):
  for offset in (284,288,292,296,308,20983):
   data=bytearray(self.sent());data[offset]=1
   with self.assertRaises(ValueError):validate(bytes(data))
 def owner(self,error):
  owner=CharacterRestore.__new__(CharacterRestore);owner.profile=PROFILE;owner.owner=42;owner.objects=self.inputs();owner.key='e33c5701000000010000000200000003'
  owner.closed=False;owner.started=False;owner.unknown=False
  def command(_,sent):
   reply=bytearray(sent);struct.pack_into('<I',reply,8,error);struct.pack_into('<I',reply,284,11 if error==4301 else 2)
   return dict(mesh_packet=bytes(reply).hex())
  owner.scope=N(_session=N(_transport=N(command=command)),close=Mock());return owner
 def test_post_dispatch_failure_retains_parameters_and_leases_without_replay(self):
  owner=self.owner(4301)
  with self.assertRaises(OriginalNarrativeError):owner.send(0)
  self.assertTrue(owner.unknown);self.assertFalse(owner.close());owner.scope.close.assert_not_called()
 def test_customization_callback_failure_is_terminal_with_stage_receipt(self):
  for stage in (14,15,16,17,18):
   owner=self.owner(4301)
   def command(_,sent):
    reply=bytearray(sent);struct.pack_into('<I',reply,8,4301);struct.pack_into('<4I',reply,284,stage,1,7,6)
    return dict(mesh_packet=bytes(reply).hex())
   owner.scope._session._transport.command=command
   with self.assertRaises(OriginalNarrativeError) as caught:owner.send(0)
   self.assertEqual(caught.exception.diagnostics,dict(stage=stage,source=1,unlocked=7,equipped=6))
   self.assertTrue(owner.unknown);self.assertFalse(owner.close());owner.scope.close.assert_not_called()
 def test_preflight_rejection_can_release_scope_without_native_cleanup(self):
  owner=self.owner(4300)
  with self.assertRaises(OriginalNarrativeError) as caught:owner.send(0)
  self.assertEqual(caught.exception.diagnostics['stage'],2);self.assertIn('stage=2',str(caught.exception));self.assertEqual(owner.diagnostics['stage'],2)
  self.assertFalse(owner.unknown);self.assertTrue(owner.close());owner.scope.close.assert_called_once()
 def test_ambiguous_transport_exception_is_terminal(self):
  owner=self.owner(0);owner.scope._session._transport.command=Mock(side_effect=TimeoutError())
  with self.assertRaises(TimeoutError):owner.send(0)
  self.assertTrue(owner.unknown);self.assertFalse(owner.close())
 def test_preparation_cannot_be_replayed_after_attempt(self):
  owner=self.owner(0);owner.attempted=True;owner.held=[]
  with self.assertRaisesRegex(RuntimeError,'one-shot'):owner.prepare(object())
 def test_empty_native_loadout_has_a_valid_preservation_receipt(self):
  sent=self.sent();reply=bytearray(self.reply(sent));struct.pack_into('<I',reply,296,0)
  self.assertEqual(decode(sent,bytes(reply))['equipped'],0)
 def transport(self,cap):
  import io
  from expedition33._session import SessionTransport
  t=SessionTransport.__new__(SessionTransport);t._check_thread=lambda:None;t._closed=False;t.mesh_protocol=3;t.character_restore_protocol=cap
  t._process=N(stdin=io.StringIO());t._read=lambda:dict(event='session_response',command='mesh',closed=False)
  return t
 def test_transport_requires_exact_advertised_capability_before_sending(self):
  for cap in (0,False,True,1,2,3,4):
   t=self.transport(cap)
   with self.assertRaisesRegex(ValueError,'Character skill.*restoration'):t.command('mesh',self.sent())
   self.assertEqual(t._process.stdin.getvalue(),'')
 def test_transport_uses_restore_packet_validator(self):
  t=self.transport(5);t.command('mesh',self.sent());self.assertTrue(t._process.stdin.getvalue().startswith('mesh '))
  t=self.transport(5);bad=bytearray(self.sent());bad[5384]=1
  with self.assertRaises(ValueError):t.command('mesh',bytes(bad))
  self.assertEqual(t._process.stdin.getvalue(),'')

class RestoreFilePacketTests(RestoreWireTests):
 def test_file_selector_is_exact_and_bounded(self):
  data=packet(42,self.inputs(),'e33c5701000000010000000200000003',slot=9,filename='EXPEDITION_9')
  self.assertEqual(struct.unpack_from('<iI',data,300),(9,13));validate(data)
  for at in (300,304,308,332,827,828):
   changed=bytearray(data);changed[at]^=1
   with self.assertRaises((RuntimeError,ValueError)):decode(data,bytes(changed))
  for slot,name in ((-1,'EXPEDITION_9'),(32,'EXPEDITION_9'),(9,None),(9,''),(9,'x'*308),(9,'a\0b')):
   with self.assertRaises(ValueError):packet(42,self.inputs(),'e33c5701000000010000000200000003',slot=slot,filename=name)
 def test_retained_save_result_releases_only_after_known_native_cleanup(self):
  owner=self.owner(0);owner.file_result=N(release=Mock(return_value=True));owner.started=False
  self.assertTrue(owner.close());self.assertIsNone(owner.file_result);owner.scope.close.assert_called_once()
  owner=self.owner(0);result=owner.file_result=N(release=Mock(return_value=True));owner.unknown=True
  self.assertFalse(owner.close());result.release.assert_not_called()

class RestoreFileFlowTests(unittest.TestCase):
 def test_original_result_lease_is_borrowed_not_reacquired_or_transferred(self):
  owner,gi,manager,loaded,_,_,_,file_call=self.setup_owner()
  owner.file_result=file_call.invoke.return_value;lease=owner.file_result._leases[0]
  self.assertIs(owner._file_source_lease(loaded),lease)
  self.assertIs(lease._scope(),owner.scope);owner.file_result.release.assert_not_called()
 def test_expired_ambiguous_foreign_or_changed_output_ownership_is_rejected(self):
  for change in ('inactive-result','foreign-result-scope','foreign-result-session','two-outputs','inactive-lease','foreign-lease-scope','foreign-lease-session','changed-object','zero-token','zero-serial'):
   owner,gi,manager,loaded,_,_,_,file_call=self.setup_owner()
   result=owner.file_result=file_call.invoke.return_value;lease=result._leases[0]
   if change=='inactive-result':result.active=False
   elif change=='foreign-result-scope':result._scope=lambda:object()
   elif change=='foreign-result-session':result._session=lambda:object()
   elif change=='two-outputs':result._leases=(lease,lease)
   elif change=='inactive-lease':lease.active=False
   elif change=='foreign-lease-scope':lease._scope=lambda:object()
   elif change=='foreign-lease-session':lease._session=lambda:object()
   elif change=='changed-object':lease.object=N(index=999,serial=2,address=0x99000)
   elif change=='zero-token':lease._token=0
   elif change=='zero-serial':loaded.serial=0
   with self.assertRaisesRegex(RuntimeError,'Original save'):owner._file_source_lease(loaded)
   result.release.assert_not_called()
 def test_result_output_ownership_failure_is_terminal_without_a_fallback_lease(self):
  from unittest.mock import patch
  owner,gi,manager,loaded,catalog,planner,_,file_call=self.setup_owner()
  file_call.invoke.return_value._leases=()
  with patch('expedition33.character_restore._file_call_catalog',return_value=catalog),patch('expedition33._stable_lease.acquire_stable',return_value=(N(object=manager),None)) as acquire:
   with self.assertRaisesRegex(RuntimeError,'one active scoped output'):owner._read_file(gi,catalog)
  self.assertTrue(owner.unknown);self.assertFalse(owner.close());acquire.assert_called_once_with(owner.scope,manager)
  file_call.invoke.return_value.release.assert_not_called();planner.close.assert_called_once()
 def test_native_cleanup_precedes_original_result_release_and_scope_cleanup(self):
  owner=CharacterRestore.__new__(CharacterRestore);events=[]
  owner.closed=False;owner.unknown=False;owner.started=True
  owner.send=lambda mode:events.append(('native',mode))
  owner.file_result=N(release=lambda:events.append('result') or True)
  owner.scope=N(close=lambda:events.append('scope'))
  self.assertTrue(owner.close());self.assertTrue(owner.close())
  self.assertEqual(events,[('native',2),'result','scope'])
 def test_preparation_keeps_original_eight_roles_and_appends_cosmetic_callbacks(self):
  from contextlib import nullcontext
  from unittest.mock import patch
  from expedition33.character_restore import FUNCTIONS,STRUCT
  obj=lambda n:N(index=n,serial=2,address=0x10000+n*16)
  gi,actor,graph=obj(1),obj(2),obj(3)
  paths={path:obj(i+4) for i,path in enumerate((*FUNCTIONS[:3],STRUCT,*FUNCTIONS[3:]))}
  owner=CharacterRestore.__new__(CharacterRestore);owner.profile=PROFILE;owner.attempted=False;owner.started=False;owner.held=[]
  owner.scope=N(pid=77);owner.resources=N(gi=gi,load=Mock(return_value=graph));owner.send=Mock(return_value={'stage':20})
  def hold(value):
   result=N(object=value);owner.held.append(result);return result
  owner.hold=hold;owner._values=Mock(return_value={'HardcodedNameID':PROFILE['character'],'SkillGraph':graph})
  preparation=N(check=Mock(),held={path:N(object=value) for path,value in paths.items()})
  with patch('expedition33.character_restore.warm',return_value=preparation),patch('expedition33._stable_lease.acquire_stable',return_value=(N(object=actor),None)),patch('expedition33._reader.shared_operation',return_value=nullcontext()):
   owner.prepare(actor)
  self.assertEqual([item.object for item in owner.objects],[gi,actor,graph,*(paths[p] for p in (*FUNCTIONS[:3],STRUCT)),graph,*(paths[p] for p in FUNCTIONS[3:])])
  owner.resources.load.assert_called_once_with(PROFILE['graph']);owner.send.assert_called_once_with(0)
  self.assertTrue(owner.started);self.assertTrue(owner.attempted)
 def setup_owner(self):
  from unittest.mock import MagicMock
  from expedition33.character_restore import CharacterRestore
  obj=lambda index,cls='Object':N(index=index,serial=2,address=0x10000+index*16,class_name=cls)
  manager=obj(1,'BP_SaveManager_C');loaded=obj(2,'BP_SaveGameObject_V8_C');gi=obj(3)
  owner=CharacterRestore.__new__(CharacterRestore);owner.held=[];owner.attempted=False;owner.unknown=False;owner.file_result=None;owner.closed=False;owner.started=False
  owner._file_context=Mock(return_value=(manager,9,'EXPEDITION_9'));owner.hold=lambda value:N(object=value)
  catalog=N(find_path=Mock(side_effect=[obj(4),obj(5),obj(6)]))
  path_result=MagicMock();path_result.__enter__.return_value=N(return_value='platform/EXPEDITION_9')
  output_lease=N(object=loaded,active=True,_token=777,_scope=lambda:owner.scope,_session=lambda:owner.scope._session)
  file_result=N(return_value=loaded,release=Mock(return_value=True),active=True,_leases=(output_lease,),
                _scope=lambda:owner.scope,_session=lambda:owner.scope._session)
  path_call=N(invoke=Mock(return_value=path_result));file_call=N(invoke=Mock(return_value=file_result))
  planner=N(prepare=Mock(side_effect=[path_call,file_call]),close=Mock())
  owner.scope=N(pid=77,_session=object(),invocation_planner=Mock(return_value=planner))
  return owner,gi,manager,loaded,catalog,planner,path_call,file_call
 def test_original_file_read_is_one_shot_retained_and_checks_selection_again(self):
  from unittest.mock import patch
  owner,gi,manager,loaded,catalog,planner,path_call,file_call=self.setup_owner()
  with patch('expedition33.character_restore._file_call_catalog',return_value=catalog),patch('expedition33._stable_lease.acquire_stable',side_effect=lambda scope,obj:(N(object=obj),None)) as acquire:
   source=owner._read_file(gi,catalog)
  self.assertIs(source.object,loaded);self.assertTrue(owner.attempted);self.assertFalse(owner.unknown)
  self.assertEqual(planner.prepare.call_args_list[0].kwargs,dict(SaveName='EXPEDITION_9'))
  self.assertEqual(planner.prepare.call_args_list[1].kwargs,dict(SlotName='platform/EXPEDITION_9',UserIndex=0))
  file_call.invoke.assert_called_once_with(fresh_results=True);self.assertEqual(owner._file_context.call_count,2)
  owner.file_result.release.assert_not_called();planner.close.assert_called_once()
  acquire.assert_called_once_with(owner.scope,manager)
  self.assertIs(source,owner.file_result._leases[0])
 def test_unknown_path_call_never_starts_read_or_replays(self):
  from unittest.mock import patch
  owner,gi,manager,loaded,catalog,planner,path_call,file_call=self.setup_owner();path_call.invoke.side_effect=TimeoutError()
  with patch('expedition33.character_restore._file_call_catalog',return_value=catalog),patch('expedition33._stable_lease.acquire_stable',side_effect=lambda scope,obj:(N(object=obj),None)):
   with self.assertRaises(TimeoutError):owner._read_file(gi,catalog)
  self.assertTrue(owner.attempted);self.assertTrue(owner.unknown);file_call.invoke.assert_not_called();planner.close.assert_called_once()
  with self.assertRaisesRegex(RuntimeError,'one-shot'):owner.prepare(loaded)
 def test_slot_change_after_file_read_is_not_a_restoration(self):
  from unittest.mock import patch
  owner,gi,manager,loaded,catalog,planner,path_call,file_call=self.setup_owner()
  owner._file_context.side_effect=[(manager,9,'EXPEDITION_9'),(manager,8,'EXPEDITION_8')]
  with patch('expedition33.character_restore._file_call_catalog',return_value=catalog),patch('expedition33._stable_lease.acquire_stable',side_effect=lambda scope,obj:(N(object=obj),None)):
   with self.assertRaisesRegex(RuntimeError,'changed during'):owner._read_file(gi,catalog)
  self.assertTrue(owner.attempted);self.assertFalse(hasattr(owner,'objects'));owner.file_result.release.assert_not_called()
 def test_warmed_file_planner_keeps_both_fresh_save_context_checks(self):
  from unittest.mock import patch
  from expedition33.character_restore import FILE_DEPENDENCIES
  owner,gi,manager,loaded,catalog,planner,path_call,file_call=self.setup_owner()
  held={path:N(object=catalog.find_path(path)) for path in FILE_DEPENDENCIES}
  preparation=N(check=Mock(),held=held,file_planner=Mock(return_value=planner))
  with patch('expedition33.catalog.capture_matching',side_effect=AssertionError('No global scan')),patch('expedition33.character_restore._file_call_catalog',side_effect=AssertionError('No repeated reflection')),patch('expedition33._stable_lease.acquire_stable',side_effect=lambda scope,obj:(N(object=obj),None)):
   result=owner._read_file(gi,preparation=preparation)
  self.assertIs(result.object,loaded);self.assertEqual(owner._file_context.call_count,2)
  preparation.file_planner.assert_called_once_with(owner.scope,manager,observed=None);preparation.check.assert_called_once_with(owner.scope)
  self.assertTrue(owner.attempted);self.assertFalse(owner.unknown);planner.close.assert_called_once()

class RestorePreparationTests(unittest.TestCase):
 def test_manager_acquisition_catalog_avoids_second_read_but_requires_exact_generation(self):
  from unittest.mock import patch
  from expedition33.character_restore import _RestorePreparation
  p=_RestorePreparation.__new__(_RestorePreparation);p.check=Mock();p.observations=object()
  planner=N(adopt_observations=Mock(),close=Mock());scope=N(pid=77,invocation_planner=Mock(return_value=planner))
  manager=N(index=2,serial=3,address=0x10000,class_name='BP_SaveManager_C',object_flags=0)
  with patch('expedition33.catalog.capture_selected',side_effect=AssertionError('No duplicate manager read')):
   fresh=N(pid=77,by_index={2:manager});self.assertIs(p.file_planner(scope,manager,observed=fresh),planner)
   planner.adopt_observations.assert_called_once_with(fresh)
   for changes in ({'serial':4},{'address':0x20000},{'object_flags':0x20},{'class_name':'OtherManager'}):
    wrong=N(pid=77,by_index={2:N(**(vars(manager)|changes))})
    with self.assertRaisesRegex(RuntimeError,'lease observation changed'):p.file_planner(scope,manager,observed=wrong)
   with self.assertRaisesRegex(RuntimeError,'lease observation changed'):p.file_planner(scope,manager,observed=N(pid=99,by_index={2:manager}))
  self.assertEqual(planner.close.call_count,5);self.assertEqual(planner.adopt_observations.call_count,1)
 def test_warm_retains_exact_dependencies_and_caches_complete_file_schemas(self):
  from contextlib import nullcontext
  from unittest.mock import patch
  from expedition33.character_restore import _RestorePreparation,DEPENDENCIES,FILE_DEPENDENCIES
  paths=(*DEPENDENCIES,*FILE_DEPENDENCIES)
  objects={path:N(index=i+1,serial=i+10,address=0x10000+i*16) for i,path in enumerate(paths)}
  held={path:N(object=obj,active=True) for path,obj in objects.items()}
  selected=object();combined=object();metadata_catalog=N(with_observations=Mock(return_value=combined))
  descriptors={i:N(object=objects[path]) for i,path in enumerate(FILE_DEPENDENCIES[:2])}
  snapshot=N(catalog=metadata_catalog,descriptors=descriptors)
  metadata=Mock();observations=object();planner=N(_metadata=metadata,observations=Mock(return_value=observations))
  scope=N(pid=77,_session=object(),invocation_planner=Mock(return_value=nullcontext(planner)))
  resources=N(scope=scope,hold=Mock(side_effect=lambda obj:next(h for h in held.values() if h.object is obj)))
  with patch('expedition33.catalog.capture_matching',return_value=N(find_path=lambda path:objects[path])) as matching,patch('expedition33.catalog.capture_selected',return_value=selected) as capture,patch('expedition33.reflection.describe_selected',return_value=snapshot) as describe:
   prepared=_RestorePreparation(resources)
  self.assertEqual(set(prepared.held),set(paths));self.assertIs(prepared.observations,observations)
  matching.assert_called_once();self.assertEqual(resources.hold.call_count,len(paths))
  expected=tuple((objects[path].index,objects[path].serial,objects[path].address) for path in FILE_DEPENDENCIES[:2])
  describe.assert_called_once_with(77,expected)
  self.assertEqual(len(capture.call_args.args[1]),len(paths))
  scope.invocation_planner.assert_called_once_with(catalog=combined,selected_results=True)
  args=metadata.read.call_args.args
  self.assertEqual(args[:3],('struct',metadata_catalog,tuple(d.object for d in descriptors.values())))
  self.assertIs(args[3](None,None),descriptors)
 def test_warm_is_process_owned_and_reused_without_a_save_or_actor(self):
  from unittest.mock import patch
  from expedition33.character_restore import warm
  resources=N(scope=N(_check=Mock()));prepared=N(check=Mock())
  with patch('expedition33.character_restore._RestorePreparation',return_value=prepared) as make:
   self.assertIs(warm(resources),prepared);self.assertIs(warm(resources),prepared)
  make.assert_called_once_with(resources);prepared.check.assert_called_once_with(resources.scope)
 def test_failed_warm_remains_journaled_and_is_never_replayed(self):
  from unittest.mock import patch
  from expedition33.character_restore import warm
  resources=N(scope=N(_check=Mock()))
  with patch('expedition33.character_restore._RestorePreparation',side_effect=TimeoutError('lease outcome unknown')) as make:
   with self.assertRaises(TimeoutError):warm(resources)
   with self.assertRaisesRegex(RuntimeError,'remains owned'):warm(resources)
  self.assertEqual(make.call_count,1);self.assertFalse(resources._character_restore_preparation['ready'])
 def test_expired_lease_or_cross_session_reuse_is_rejected(self):
  from expedition33.character_restore import _RestorePreparation
  p=_RestorePreparation.__new__(_RestorePreparation);p.session=object()
  p.resources=N(scope=N(_check=Mock()));scope=N(_session=p.session,_check=Mock());p.held={'function':N(active=True)}
  p.check(scope)
  scope._session=object()
  with self.assertRaisesRegex(RuntimeError,'ownership changed'):p.check(scope)
  scope._session=p.session;p.held['function'].active=False
  with self.assertRaisesRegex(RuntimeError,'ownership changed'):p.check(scope)
 def test_file_planner_recaptures_selected_manager_even_with_warm_metadata(self):
  from unittest.mock import patch
  from expedition33.character_restore import _RestorePreparation
  p=_RestorePreparation.__new__(_RestorePreparation);p.check=Mock();p.observations=object()
  planner=N(adopt_observations=Mock(),close=Mock());scope=N(pid=77,invocation_planner=Mock(return_value=planner))
  manager=N(index=2,serial=3,address=0x10000,class_name='BP_SaveManager_C',object_flags=0)
  fresh=N(pid=77,by_index={manager.index:manager})
  with patch('expedition33.catalog.capture_selected',return_value=fresh) as capture:
   self.assertIs(p.file_planner(scope,manager),planner)
  capture.assert_called_once_with(77,((2,3,0x10000),));planner.adopt_observations.assert_called_once_with(fresh)
  scope.invocation_planner.assert_called_once_with(observations=p.observations,selected_results=True)
  with patch('expedition33.catalog.capture_selected',side_effect=RuntimeError('identity changed')):
   with self.assertRaisesRegex(RuntimeError,'identity changed'):p.file_planner(scope,manager)
  planner.close.assert_called_once()

class RestorePostReadContextTests(unittest.TestCase):
 def fixture(self):
  from expedition33.values import StoredValues
  owner=CharacterRestore.__new__(CharacterRestore);owner.scope=N(pid=77)
  gi=N(index=10,serial=11,address=0x10000,object_flags=0,class_name='BP_jRPG_GI_Custom_C')
  manager=N(index=20,serial=21,address=0x20000,object_flags=0,class_name='BP_SaveManager_C')
  fields=[{'SaveManager':manager,'LastRelevantSaveName':'EXPEDITION_9'},
          {'GameInstanceReference':gi,'SelectedSlot':9,'LoadIsInProgress':False,'SaveIsInProgress':False}]
  rows={obj.index:StoredValues(obj,{('Owner',name):value for name,value in values.items()},{},{('Owner',name):'field' for name in values}) for obj,values in zip((gi,manager),fields)}
  return owner,gi,manager,N(by_index={gi.index:gi,manager.index:manager}),rows
 def test_gi_and_expected_manager_are_freshly_observed_together(self):
  from unittest.mock import patch
  owner,gi,manager,catalog,rows=self.fixture()
  with patch('expedition33.values.capture_selected_values',return_value=(catalog,rows)) as capture:
   self.assertEqual(owner._file_context(gi,manager),(manager,9,'EXPEDITION_9'))
  capture.assert_called_once_with(77,((10,11,0x10000),(20,21,0x20000)),fields=('SaveManager','LastRelevantSaveName','GameInstanceReference','SelectedSlot','LoadIsInProgress','SaveIsInProgress'),references=True)
 def test_replaced_manager_or_wrong_gi_cannot_pass_combined_read(self):
  from unittest.mock import patch
  from dataclasses import replace
  for index,name in ((10,'SaveManager'),(20,'GameInstanceReference')):
   owner,gi,manager,catalog,rows=self.fixture();row=rows[index]
   rows[index]=replace(row,values={**row.values,('Owner',name):N(index=99,serial=100,address=0x90000)})
   with patch('expedition33.values.capture_selected_values',return_value=(catalog,rows)):
    with self.assertRaisesRegex(RuntimeError,'manager'):owner._file_context(gi,manager)
 def test_partial_or_destroyed_observation_cannot_pass_combined_read(self):
  from unittest.mock import patch
  from dataclasses import replace
  for index in (10,20):
   for change in ('errors','truncated','generation','destroyed'):
    owner,gi,manager,catalog,rows=self.fixture()
    if change in ('errors','truncated'):rows[index]=replace(rows[index],**{change:{('Owner','field'):'failed'}})
    else:catalog.by_index[index]=N(**(vars(catalog.by_index[index])|({'serial':999} if change=='generation' else {'object_flags':0x20})))
    with patch('expedition33.values.capture_selected_values',return_value=(catalog,rows)):
     with self.assertRaisesRegex(RuntimeError,'changed or is incomplete'):owner._file_context(gi,manager)
 def test_busy_slot_and_filename_fields_are_rechecked_not_inherited(self):
  from unittest.mock import patch
  from dataclasses import replace
  for index,name,value in ((20,'LoadIsInProgress',True),(20,'SaveIsInProgress',True),(20,'SelectedSlot',32),(10,'LastRelevantSaveName','bad\0name')):
   owner,gi,manager,catalog,rows=self.fixture();row=rows[index]
   rows[index]=replace(row,values={**row.values,('Owner',name):value})
   with patch('expedition33.values.capture_selected_values',return_value=(catalog,rows)):
    with self.assertRaises(RuntimeError):owner._file_context(gi,manager)

class RestoreFileCatalogTests(unittest.TestCase):
 def test_non_parameter_local_type_is_selected_before_strict_planning(self):
  from unittest.mock import patch
  from expedition33 import RuntimeQueryError
  from expedition33.catalog import Catalog,CatalogObject,ClassRelation
  from expedition33.reflection import describe
  from expedition33.character_restore import _file_call_catalog
  from test_invocation import InvocationTests
  fixture=InvocationTests();fixture.setUp();base=fixture.catalog
  local=CatalogObject(123,2995,8,0x90000,'PlatformsSubsystem','Class','Class',1,-1,0,0,0)
  second=CatalogObject(123,8,1,0x5000,'LoadGameFromSlot','Function','Class',6,2,1,0,0)
  complete=Catalog(123,(*base.objects,local,second),(*base.classes.values(),ClassRelation(2995,8,'PlatformsSubsystem',0,128)))
  first=base.by_index[7];manager=base.by_index[5];cdo=base.by_index[4]
  selected=complete.subset((manager,first,second,cdo))
  self.assertNotIn(2995,selected.by_index)
  def rows(obj):
   return [dict(event='object',index=obj.index,serial=obj.serial,address=hex(obj.address),name=obj.name,class_index=obj.class_index),dict(event='struct_metadata',index=obj.index,serial=obj.serial,address=hex(obj.address),name=obj.name,size=56)]
  first_rows=rows(first)+[dict(event='property_metadata',name='CallFunc_GetGameInstanceSubsystem_ReturnValue',type='ObjectProperty',offset=32,element_size=8,dimension=1,flags=hex(2251868533162496),property_class_index=2995,property_class_serial=8,property_class_name='PlatformsSubsystem',property_class_address=hex(local.address))]
  with patch('expedition33.reflection._query',return_value=({'pid':123},first_rows)):
   with self.assertRaisesRegex(RuntimeQueryError,'2995'):describe(selected,(first,))
  with patch('expedition33.catalog.capture_selected',side_effect=[selected,selected,complete]) as capture,patch('expedition33.reflection._query',return_value=({'pid':123},first_rows+rows(second))):
   planned=_file_call_catalog(123,manager,(N(object=first),N(object=second),N(object=cdo)))
  self.assertEqual(capture.call_args_list[-1].args,(123,((2995,8,0x90000),)))
  with patch('expedition33.reflection._query',return_value=({'pid':123},first_rows)):
   self.assertEqual(describe(planned,(first,))[7].properties[0]['property_class_index'],2995)
  self.assertEqual(planned.resolve(manager),manager)
  self.assertEqual(planned.resolve(cdo),cdo)
