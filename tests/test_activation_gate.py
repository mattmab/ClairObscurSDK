import importlib.util,sys,threading,unittest
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import RuntimeQueryError
from expedition33 import world_admission as m
class Tests(unittest.TestCase):
 def setUp(self):
  kinds=('GameEngine','GameViewportClient','World','BP_jRPG_GI_Custom_C','BP_SaveManager_C','LocalPlayer','PlayerController','BP_jRPG_Character_World_C')
  self.objects=tuple(N(pid=7,index=i+1,serial=1,address=100+i,class_index=20+i,class_name=kind,object_flags=0) for i,kind in enumerate(kinds))
  self.binding=tuple(m.identity(o) for o in self.objects)
  self.catalog=N(by_index={o.index:o for o in self.objects},find_class=lambda kind:N(index=20+kinds.index(kind)),ancestors=lambda cls:(cls,),outer_chain=lambda obj:(self.objects[2],))
  e,v,w,g,s,l,c,p=self.objects
  self.rows={o.index:N(types={},values={},errors={},truncated=set()) for o in self.objects[:-1]}
  for obj,name,target in ((e,'GameViewport',v),(v,'World',w),(w,'OwningGameInstance',g),(g,'SaveManager',s),(s,'GameInstanceReference',g),(l,'PlayerController',c),(c,'Player',l),(c,'Pawn',p)):
   self.field(obj,name,'ObjectProperty',target)
  self.field(g,'LocalPlayers','ArrayProperty',m.StoredArray((l,),1))
  self.field(g,'SaveLoaded','BoolProperty',True);self.field(s,'LoadIsInProgress','BoolProperty',False);self.field(s,'SelectedSlot','IntProperty',0)
  self.observer=m.WarmAdmissionObserver.__new__(m.WarmAdmissionObserver)
  self.observer.pid=7;self.observer._owner=threading.get_ident();self.observer._closed=False
  self.observer._reader=N(bind=lambda:nullcontext(),close=Mock());self.observer._engine=(1,1,100)
  self.observer._activation_binding=self.binding;self.observer.observe=Mock(side_effect=AssertionError('no same-call fallback'))
 def field(self,obj,name,kind,value):
  row=self.rows[obj.index];key=(obj.class_index,name);row.types[key]=kind;row.values[key]=value
 def run_gate(self,values=None,catalog=None):
  with patch('expedition33.catalog.capture_selected',return_value=catalog or self.catalog) as capture,patch('expedition33.values.read_values_many',side_effect=values,return_value=self.rows) as read:
   result=self.observer.observe_activation()
   return result,capture,read
 def test_complete_two_pass_gate_uses_four_bounded_queries_no_discovery(self):
  result,capture,read=self.run_gate()
  self.assertTrue(result.activation_ready);self.assertEqual(capture.call_count,2);self.assertEqual(read.call_count,2)
  self.assertEqual(capture.call_args.args[1],tuple(row[1:] for row in self.binding))
  self.assertEqual(len(read.call_args.kwargs['fields']),12);self.observer.observe.assert_not_called()
 def test_changed_reciprocal_reference_holds_without_same_call_retry(self):
  self.field(self.objects[6],'Player','ObjectProperty',self.objects[0])
  result,capture,read=self.run_gate();self.assertEqual(result.state,'observation_pending')
  self.assertEqual(capture.call_count,1);self.assertEqual(read.call_count,1)
  self.assertIsNone(self.observer._activation_binding);self.observer.observe.assert_not_called()
 def test_changed_second_pass_flags_are_pending(self):
  calls=[0]
  def read(*args,**kwargs):
   calls[0]+=1
   if calls[0]==2:self.field(self.objects[4],'SelectedSlot','IntProperty',1)
   return self.rows
  result,_,_=self.run_gate(values=read);self.assertEqual(result.reason,'activation_context_changed')
 def test_complete_array_membership_is_required(self):
  self.field(self.objects[3],'LocalPlayers','ArrayProperty',m.StoredArray((self.objects[5],),2))
  result,_,_=self.run_gate();self.assertEqual(result.reason,'activation_membership_changed')
 def test_loading_remains_explicit_inactive_activation(self):
  self.field(self.objects[4],'LoadIsInProgress','BoolProperty',True)
  result,_,_=self.run_gate();self.assertEqual(result.state,'loading');self.assertFalse(result.activation_ready)
 def test_schema_owner_mismatch_stays_visible_and_discards_worker(self):
  row=self.rows[1];row.types={(999,'GameViewport'):'ObjectProperty'}
  reader=self.observer._reader
  with self.assertRaisesRegex(RuntimeQueryError,'provenance'):
   self.run_gate()
  reader.close.assert_called_once();self.assertIsNone(self.observer._activation_binding)
 def test_invalid_boolean_type_stays_visible(self):
  self.field(self.objects[3],'SaveLoaded','BoolProperty',1)
  with self.assertRaisesRegex(RuntimeQueryError,'save flags invalid'):self.run_gate()
 def test_stale_selector_exception_is_not_retried(self):
  reader=self.observer._reader
  with patch('expedition33.catalog.capture_selected',side_effect=RuntimeQueryError('SELECTED_DEPENDENCY_CHANGED')) as capture:
   with self.assertRaises(RuntimeQueryError):self.observer.observe_activation()
  capture.assert_called_once();reader.close.assert_called_once();self.observer.observe.assert_not_called()
 def test_missing_binding_uses_full_observation_on_next_scheduled_call(self):
  self.observer._activation_binding=None;self.observer.observe=Mock(return_value=m.Admission('observation_pending','test'))
  self.assertEqual(self.observer.observe_activation().reason,'test');self.observer.observe.assert_called_once()
 def test_controller_outer_and_pawn_reference_must_match(self):
  self.catalog.outer_chain=lambda obj:()
  result,_,_=self.run_gate();self.assertEqual(result.reason,'activation_controller_world_changed')
 def test_scope_owner_thread_is_required_before_any_query(self):
  self.observer._owner=-1
  with patch.object(m,'capture_selected_values') as capture:
   with self.assertRaisesRegex(RuntimeError,'owner thread'):self.observer.observe_activation()
  capture.assert_not_called()
 def test_plain_warm_controller_records_current_selector_for_fast_binding(self):
  local=self.objects[5];pc=self.objects[6];world=self.objects[2]
  row=N(types={(local.class_index,'PlayerController'):'ObjectProperty'})
  self.catalog.by_index[local.class_index]=object()
  with patch.object(m,'read_values_with_references',return_value=(self.rows[4],self.catalog)),patch.object(m,'read_values_many',return_value={local.index:row}),patch.object(m,'read_object_reference',return_value=(pc,self.catalog)):
   current=self.observer.controller(self.catalog,self.objects[3])
  self.assertEqual(self.observer._ui_controller,m.identity(pc))
  self.assertEqual(current['world'],m.identity(world))
 def test_successful_full_observation_establishes_selected_binding_once(self):
  observer=m.WarmAdmissionObserver(7)
  reader=N(bind=lambda:nullcontext(),_closed=False,close=Mock())
  def full(pid,provider):
   provider._ui_anchor=self.binding[:4];provider._ui_local_player=self.binding[5]
   provider._ui_controller=self.binding[6];provider._ui_pawn=self.binding[7]
   return m.Admission('world_ready','exploration_ready',(self.binding[2],self.binding[3],self.binding[4],0),True)
  with patch.object(m,'ReadBatch',return_value=reader),patch.object(m,'_read_admission',side_effect=full):
   self.assertTrue(observer.observe_activation().activation_ready)
  self.assertEqual(observer._activation_binding,self.binding)
  observer.close()

if __name__=='__main__':unittest.main()
