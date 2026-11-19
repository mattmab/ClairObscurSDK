import sys,types,unittest
from pathlib import Path
from types import SimpleNamespace as NS
p=types.ModuleType('damage_presentation_test');p.__path__=[str(Path('mods/SkillDamage').resolve())];sys.modules[p.__name__]=p
from damage_presentation_test.presentation import skill_panel,number_range
from damage_presentation_test.forecast import Outcomes
from damage_presentation_test.row_panel import DamageRows,PALETTE

class PresentationTests(unittest.TestCase):
 def test_base_extra_and_full_total_keep_all_four_cases(self):
  out=Outcomes(100,150,120,180)
  audit=dict(extra_lower=(10,15,12,18),extra_upper=(20,30,24,36))
  text=skill_panel(out,audit,('extra hit','Aureole','rank gain'),'Physical: Neutral',10000)
  rows=text.damage_rows
  self.assertEqual([r.kind for r in rows],['heading','fail','pass','extra','total_heading','total_fail','total_pass','metadata'])
  self.assertEqual((rows[1].normal,rows[1].critical),('100','150'))
  self.assertEqual((rows[2].normal,rows[2].critical),('120','180'))
  self.assertEqual((rows[3].normal,rows[3].critical),('10-24','15-36'))
  self.assertEqual((rows[5].normal,rows[5].critical),('110-120','165-180'))
  self.assertEqual((rows[6].normal,rows[6].critical),('132-144','198-216'))
  self.assertEqual(rows[-1].label,'Physical: Neutral | Rank +')
 def test_no_qte_or_extra_has_only_applicable_rows(self):
  text=skill_panel(Outcomes(100,150,100,150),dict(extra_lower=(0,)*4,extra_upper=(0,)*4),(),'Light: Neutral',10000)
  self.assertEqual([r.label for r in text.damage_rows],['BASE DAMAGE','HIT','TOTAL ATTACK','HIT','Light: Neutral'])
 def test_qte_rows_remain_when_target_hp_caps_results_to_equal_values(self):
  audit=dict(extra_lower=(0,)*4,extra_upper=(0,)*4,failed=[{'coefficient':1}],passed=[{'coefficient':1.1}])
  rows=skill_panel(Outcomes(5,5,5,5),audit,(),'Physical: Neutral',5).damage_rows
  self.assertEqual(sum(r.label=='PASS' for r in rows),2)
 def test_close_range_does_not_collapse_to_one_abbreviated_value(self):
  self.assertEqual(number_range(10001,10002),'10.001-10.002k')
  self.assertEqual(number_range(1000001,1000002),'1.000001-1.000002m')
 def test_permanent_rows_only_repaint_numbers_when_values_change(self):
  calls=[]
  owner=NS(frame='frame',_call=lambda *a,**k:calls.append((a,k)),_setters=lambda x:calls.append(('layout',x)))
  panel=DamageRows(owner,'canvas','label');panel.labels=['label','n','c'];panel.backgrounds=[('b'+str(i),'s'+str(i)) for i in range(8)]
  panel.total_labels=[('t'+str(i),'ts'+str(i)) for i in range(4)];panel.separator='sep';panel.separator_slot='sep-slot'
  audit=dict(extra_lower=(0,)*4,extra_upper=(0,)*4)
  panel.update(skill_panel(Outcomes(100,150,120,180),audit,(),'Physical: Neutral',10000));calls.clear()
  panel.update(skill_panel(Outcomes(101,151,121,181),audit,(),'Physical: Neutral',10000))
  self.assertEqual(len(calls),1)
  self.assertEqual(calls[0][0],'layout')
  self.assertTrue(all(x[2]=='SetText' for x in calls[0][1]))
  calls.clear();panel.set_expanded(True)
  batches=[x[1] for x in calls if x[0]=='layout']
  self.assertEqual(len(batches),1)
  self.assertFalse(any(x[1]=='CanvasPanelSlot' for x in batches[0]))
 def test_batched_construction_adopts_background_and_total_slots_in_order(self):
  calls=[];groups=[]
  objects=[NS(name='Default__GameplayStatics')]
  catalog=NS(objects=objects,by_index={1:'class'},find_class=lambda _:NS(index=1))
  def invoke(obj,owner,name,**args):
   calls.append((owner,name));return NS(return_value={'Y':80.})
  owner=NS(catalog=catalog,tree='tree',frame='frame',_call=invoke,_setters=lambda rows:None,_enum=lambda *args:3)
  panel=DamageRows(owner,'canvas','first')
  def group(rows):
   groups.append(rows);return list(range(100,100+len(rows))) if len(groups)==1 else list(range(200,200+len(rows)))
  panel.group=group;panel.build_batched()
  self.assertEqual([len(group) for group in groups],[19,17])
  self.assertEqual([slot for _,slot in panel.backgrounds],list(range(200,208)))
  self.assertEqual([slot for _,slot in panel.total_labels],list(range(212,216)))
  self.assertEqual(panel.separator_slot,216)
  self.assertFalse(any(name=='SpawnObject' for _,name in calls))
 def test_muted_outcome_colors_are_distinct_and_total_has_more_emphasis(self):
  self.assertGreater(PALETTE['fail'][0],PALETTE['fail'][1])
  self.assertGreater(PALETTE['pass'][1],PALETTE['pass'][0])
  self.assertGreater(PALETTE['total_pass'][3],PALETTE['pass'][3])

class CollapsedDetailsTests(unittest.TestCase):
 def full(self):
  audit=dict(extra_lower=(10,15,12,18),extra_upper=(20,30,24,36))
  return skill_panel(Outcomes(100,150,120,180),audit,('extra hit','rank gain'),'Physical: Neutral',10000).damage_rows
 def test_default_has_only_four_rows_and_full_combined_values(self):
  from damage_presentation_test.presentation import visible_rows
  rows=visible_rows(self.full())
  self.assertEqual([r.kind for r in rows],['total_heading','total_fail','total_pass','metadata'])
  self.assertIn('> Damage Details [Alt]',rows[0].normal)
  self.assertEqual((rows[1].normal,rows[1].critical),('110-120','165-180'))
  self.assertEqual((rows[2].normal,rows[2].critical),('132-144','198-216'))
 def test_expansion_reorders_without_removing_any_damage_values(self):
  from damage_presentation_test.presentation import visible_rows
  source=self.full();rows=visible_rows(source,True)
  self.assertEqual([r.kind for r in rows],['total_heading','total_fail','total_pass','heading','fail','pass','extra','metadata'])
  self.assertEqual(set((r.kind,r.normal,r.critical) for r in rows[1:]),set((r.kind,r.normal,r.critical) for r in source if r.kind!='total_heading'))
 def test_each_panel_has_its_own_expansion_state(self):
  a=DamageRows(None,None,None);b=DamageRows(None,None,None)
  a.set_expanded(True);self.assertTrue(a.expanded);self.assertFalse(b.expanded)
  a.set_expanded(False);self.assertFalse(a.expanded)
 def test_modifier_ignores_alt_when_other_application_has_focus(self):
  import ctypes
  from damage_presentation_test.details_input import DetailsModifier
  calls=[]
  def pid(window,pointer):pointer._obj.value=999
  user=NS(GetForegroundWindow=lambda:1,GetWindowThreadProcessId=pid,GetAsyncKeyState=lambda key:calls.append(key) or -32768)
  modifier=DetailsModifier.__new__(DetailsModifier);modifier.pid=123;modifier.user=user;modifier.ctypes=ctypes
  self.assertFalse(modifier.held());self.assertEqual(calls,[])
  modifier.pid=999;self.assertTrue(modifier.held());self.assertEqual(calls,[0x12])

class PendingDamageRowsTests(unittest.TestCase):
 def test_stale_sample_keeps_rows_height_and_numbers_and_marks_cached_values(self):
  calls=[]
  owner=NS(frame='frame',_call=lambda *a,**k:calls.append((a,k)),_setters=lambda x:self.fail('Must not rebuild layout'))
  panel=DamageRows(owner,'canvas','label');panel.labels=['label','n','c']
  panel.column_text=['\nFAIL\nPASS\nPhysical: Neutral','N 100\nN 120','C 150\nC 180'];panel.last_count=90;panel.kinds=('total_heading','total_fail','total_pass','metadata')
  panel.set_pending(True)
  self.assertEqual(panel.last_count,90)
  self.assertEqual(panel.column_text[1],'N 100\nN 120')
  self.assertIn('Updating damage...',calls[0][1]['InText'])
  self.assertTrue(all(c[0][2] in ('SetText','SetRenderOpacity') for c in calls))
  calls.clear();panel.set_pending(True);self.assertEqual(calls,[])
  panel.set_pending(False)
  self.assertEqual(calls[0][1]['InText'],'\nFAIL\nPASS\nPhysical: Neutral')

class PlanningCacheTests(unittest.TestCase):
 def test_reusable_definitions_exclude_recyclable_widget_instances(self):
  from damage_presentation_test.ui import definition_catalog
  rows=[NS(index=1,class_name='Class',object_flags=0),NS(index=2,class_name='Function',object_flags=0),NS(index=3,class_name='Enum',object_flags=0),NS(index=4,class_name='ScriptStruct',object_flags=0),NS(index=5,class_name='Border',object_flags=0x10),NS(index=6,class_name='Border',object_flags=0),NS(index=7,class_name='SizeBox',object_flags=0)]
  catalog=NS(objects=rows,classes={1:object()},subset=lambda selected:tuple(o.index for o in selected))
  self.assertEqual(definition_catalog(catalog),(1,2,3,4,5))

class LabelLifecycleTests(unittest.TestCase):
 def test_build_keeps_only_owned_card_closure_before_merging(self):
  from damage_presentation_test.ui import DamageLabel
  from unittest.mock import Mock
  owner=DamageLabel.__new__(DamageLabel);owner.card='card';owner.tree='tree';owner.parent=NS(class_name='unexpected');owner.description='description';owner.visibility_source=None
  definitions=Mock();observations=Mock();owner.definitions=(definitions,{})
  with self.assertRaisesRegex(RuntimeError,'Unknown skill card layout'):owner.build(observations)
  observations.subset.assert_called_once_with(('card','tree',owner.parent,'description'))
  definitions.with_observations.assert_called_once_with(observations.subset.return_value)
 def test_returned_construction_failure_allows_cleanup_without_replaying(self):
  from damage_presentation_test.ui import DamageLabel
  from expedition33.invocation import InvocationError
  from unittest.mock import Mock
  for outcome,uncertain in (('dispatch_returned',False),('not_dispatched',False),('unknown',True)):
   owner=DamageLabel.__new__(DamageLabel);owner.uncertain=False;owner._function=lambda *a:'function'
   call=Mock();call.invoke.side_effect=InvocationError('test',outcome=outcome);owner.planner=NS(prepare=lambda *a,**k:call)
   with self.assertRaises(InvocationError):owner._call('target','Widget','RemoveFromParent')
   self.assertEqual(owner.uncertain,uncertain);self.assertEqual(call.invoke.call_count,1)

class ReparentingResultTests(unittest.TestCase):
 def test_reparenting_decodes_fresh_slot_outputs_without_merging_replaced_slots(self):
  from damage_presentation_test.ui import DamageLabel
  calls=[];catalog=object()
  prepared=NS(invoke=lambda **kwargs:calls.append(kwargs) or 'returned')
  owner=DamageLabel.__new__(DamageLabel);owner.uncertain=False
  owner.planner=NS(prepare=lambda *args,**kwargs:prepared,_catalog=catalog)
  owner._function=lambda *args:'function'
  self.assertEqual(owner._call('parent','ContentWidget','SetContent',Content='original'),'returned')
  self.assertEqual(calls,[{'fresh_results':True}]);self.assertIs(owner.catalog,catalog)
  calls.clear();owner._call('parent','ContentWidget','GetContent')
  self.assertEqual(calls,[{'refresh_from_result':True}])

class HealthProjectionTests(unittest.TestCase):
 def test_shared_bar_accepts_only_reciprocal_live_links_of_its_master(self):
  from damage_presentation_test.observe import projection_targets,identity
  a=NS(index=1,serial=10,address=100);b=NS(index=2,serial=20,address=200);unrelated=NS(index=3,serial=30,address=300)
  rows={1:dict(bIsLifeLinkMaster=True,LifeLinkedCharacters=NS(items=(b,),length=1)),2:dict(bIsLifeLinkMaster=False,LifeLinkedCharacters=NS(items=(a,),length=1))}
  self.assertEqual(projection_targets(a,(a,b,unrelated),rows),(identity(a),identity(b)))
  self.assertEqual(projection_targets(a,(a,unrelated),rows),(identity(a),))
  self.assertEqual(projection_targets(b,(a,b),rows),(identity(b),))
  rows[2]['LifeLinkedCharacters']=NS(items=(),length=0)
  self.assertEqual(projection_targets(a,(a,b),rows),(identity(a),))
 def test_combined_range_includes_extra_hits_and_clamps_to_remaining_health(self):
  from damage_presentation_test.bar_projection import loss_range,segments
  model=dict(failed_normal=100,failed_critical=150,passed_normal=120,passed_critical=180,inputs=dict(extra_lower=(10,15,12,18),extra_upper=(20,30,24,36)))
  self.assertEqual(loss_range(model,1000),(110,216))
  self.assertEqual(loss_range(model,200),(110,200))
  possible,minimum=segments(1000,.5,loss_range(model,1000))
  self.assertAlmostEqual(possible[0],.392);self.assertAlmostEqual(possible[1],.445)
  self.assertEqual(minimum,(.445,.5))
 def test_unavailable_or_invalid_forecasts_never_paint_a_damage_chunk(self):
  from damage_presentation_test.bar_projection import loss_range,segments
  self.assertIsNone(loss_range(None,100))
  self.assertIsNone(loss_range({'inputs':{'extra_unavailable':'pending'}},100))
  self.assertIsNone(segments(100,0.,(1,2)))

class ProjectionCanvasLayoutTests(unittest.TestCase):
 def test_canvas_fills_the_native_health_bar_instead_of_zero_desired_size(self):
  from damage_presentation_test.bar_projection import BarProjection
  batches=[];counter=[0]
  catalog=NS(objects=[NS(name='Default__GameplayStatics')],by_index={1:'class'},find_class=lambda _:NS(index=1))
  catalog.with_observations=lambda _:catalog
  owner=BarProjection.__new__(BarProjection)
  owner.card='card';owner.tree='tree';owner.parent='parent';owner.progress_slot='progress-slot';owner.padding=dict(Left=0.,Top=0.,Right=0.,Bottom=0.)
  owner.definitions=(catalog,{});owner.scope=NS(invocation_planner=lambda **kwargs:NS())
  def call(*args,**kwargs):counter[0]+=1;return NS(return_value='object'+str(counter[0]))
  owner._call=call;owner._setters=lambda rows:batches.extend(rows);owner._enum=lambda _,v:v
  owner.build(NS(subset=lambda _:None))
  alignment=[(name,args) for _,kind,name,args in batches if kind=='OverlaySlot']
  self.assertIn(('SetHorizontalAlignment',{'InHorizontalAlignment':0}),alignment)
  self.assertIn(('SetVerticalAlignment',{'InVerticalAlignment':0}),alignment)

class DamageTreeCleanupTests(unittest.TestCase):
 def test_row_cleanup_does_not_dispatch_per_child_mutations(self):
  owner=NS(_call=lambda *a,**k:self.fail('Root owner detaches before releasing its children'))
  panel=DamageRows(owner,'canvas','label');panel.children=list(range(19));panel.close()
  self.assertEqual(panel.children,[])
 def test_support_first_render_hides_the_prebuilt_total_attack_heading(self):
  calls=[];owner=NS(_call=lambda *a,**k:calls.append((a,k)),_setters=lambda rows:None,frame='frame')
  panel=DamageRows(owner,'canvas','label');panel.heading='heading';panel.separator='separator'
  from damage_presentation_test.presentation import DamageText,DamageRow
  panel.update(DamageText((DamageRow('metadata','Support skill | No direct attack damage'),)))
  self.assertIn((('heading','Widget','SetRenderOpacity'),{'InOpacity':0.}),calls)
  self.assertIn((('separator','Widget','SetRenderOpacity'),{'InOpacity':0.}),calls)
 def test_pending_rows_do_not_flash_opacity(self):
  calls=[];owner=NS(_call=lambda *a,**k:calls.append(a))
  panel=DamageRows(owner,'canvas','label');panel.column_text=['footer',None,None]
  panel.set_pending(True);panel.set_pending(False)
  self.assertTrue(all(c[2]=='SetText' for c in calls))
