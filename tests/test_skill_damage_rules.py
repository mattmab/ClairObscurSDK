import sys,types,time,unittest
from pathlib import Path
from types import SimpleNamespace as NS
package=types.ModuleType('skill_damage_rules_test');package.__path__=[str(Path('mods/SkillDamage').resolve())];sys.modules[package.__name__]=package
from skill_damage_rules_test.rules import prediction,predict
from skill_damage_rules_test.forecast import Outcomes
from skill_damage_rules_test.mod import Mod
from unittest.mock import patch

def mapped(values):return NS(items=values)
def context():
 return dict(skill={'NameID':'QuickStrike','SkillScript':NS(asset='BP_Battle_SkillScript_NEW_QuickStrike_C')},
  source={'CharacterCurrentStats':mapped({1:100,3:100}),'CurrentHP':100},
  target={'CharacterCurrentStats':mapped({6:0}),'CharacterStats':NS(truncated=False,errors={},fields={'ReceivedSkillDamageMultiplier':1.}), 'CurrentHP':10000,'CurrentShieldPoints':0},
  source_buffs=(),target_buffs=(),tables={'DT_Balancing_MainCharacterSkills':{'QuickStrike_BaseDamage':1.,'Generic_DamageIncreaseForEachQTE':.1},'DT_Balancing_Luminas':{}},
  state={'IsOvercharged':False,'ElementalType':1},affinities=mapped({}),party_count=1,extras={},qte_per_hit=(1,),catalog=None)
class RuleTests(unittest.TestCase):
 def test_maelle_equipped_damage_skills_use_live_coefficients_and_qtes(self):
  cases=(('OffensiveSwitch','BP_Battle_SkillScript_OffensiveSwitch_C',1.,(1,),Outcomes(100,150,110,165)),
         ('Percee','BP_Battle_SkillScript_New14_Percee_C',2.2,(1,),Outcomes(220,330,242,363)),
         ('Spark','BP_Battle_SkillScript_New18_Spark_C',1.,(2,),Outcomes(100,150,120,180)),
         ('FireRise','BP_Battle_SkillScript_New4_FireRise_C',1.,(0,),Outcomes(100,150,100,150)))
  for name,script,coefficient,qte,expected in cases:
   with self.subTest(skill=name):
    c=context();c['skill']={'NameID':name,'SkillScript':NS(asset=script)};c['qte_per_hit']=qte
    c['tables']['DT_Balancing_MainCharacterSkills'][name+'_BaseDamage']=coefficient
    self.assertEqual(prediction(c)[0],expected)
 def test_percee_uses_its_own_mark_bonus_and_the_live_mark_multiplier(self):
  c=context();c['skill']={'NameID':'Percee','SkillScript':NS(asset='BP_Battle_SkillScript_New14_Percee_C')}
  c['tables']['DT_Balancing_MainCharacterSkills'].update(Percee_BaseDamage=2.2,Percee_MarkedDamageMultiplier=2.)
  c['target_buffs']=(NS(class_name='BP_BattleBuff_Marked_C',index=77,class_index=77),)
  c['extras']={77:{'HitCountToRemoveMark':1,'ModifyDamageElements':False,'IsMarkedForRemoval':False}}
  c['catalog']=NS(classes={},ancestors=lambda _:())
  self.assertEqual(prediction(c)[0],Outcomes(660,990,726,1089))
 def test_support_skills_do_not_show_fictitious_damage_totals(self):
  from skill_damage_rules_test.rules import predict
  for name,script in (('MezzoForte','BP_Battle_SkillScript_New11_MezzoForte_C'),('LastChance','BP_Battle_SkillScript_LastChance_C')):
   c=context();c['skill']={'NameID':name,'SkillScript':NS(asset=script)};c['target']=None
   text=predict(c);self.assertIn('No direct attack damage',text);self.assertNotIn('TOTAL ATTACK',text)
 def test_current_target_defense_affinity_and_timed_cases(self):
  c=context();c['target']['CharacterCurrentStats']=mapped({6:50});c['affinities']=mapped({1:2})
  result,_=prediction(c)
  self.assertEqual(result,Outcomes(75,113,86,130))
 def test_unreviewed_skill_or_changed_script_has_no_estimate(self):
  for skill in ({'NameID':'Unknown','SkillScript':None},{'NameID':'QuickStrike','SkillScript':NS(asset='changed')}):
   c=context();c['skill']=skill
   with self.assertRaises(ValueError):prediction(c)
 def test_shield_and_remaining_hp_are_target_specific(self):
  c=context();c['target']['CurrentShieldPoints']=1
  self.assertEqual(prediction(c)[0],Outcomes(0,0,0,0))
  c['target']['CurrentShieldPoints']=0;c['target']['CurrentHP']=70
  self.assertEqual(prediction(c)[0],Outcomes(70,70,70,70))
 def test_live_failed_quickstrike_critical_regression(self):
  c=context();c['source']['CharacterCurrentStats']=mapped({1:3809,3:11583})
  buffs=[NS(class_name=n,class_index=i,index=i) for i,n in enumerate(('BP_LU_GlassCanon_C','BP_LU_SoloFighter_C','BP_LU_ConfidentFighter_C','BP_LU_Overpowered_C'))]
  c['target']['CurrentHP']=444534;c['source_buffs']=buffs;c['catalog']=NS(classes={},ancestors=lambda _:())
  c['tables']['DT_Balancing_Luminas']={'GlassCanon_DamageMultiplier':1.25,'SoloFighter_DamageMultiplier':1.5,'ConfidentFighter_DamageIncrease':.3}
  self.assertEqual(prediction(c)[0].failed_critical,42350)
 def test_fast_poll_cannot_starve_widget_construction(self):
  from skill_damage_rules_test import ui
  now=time.monotonic();cards=[(NS(index=i,serial=1,address=65536+i*8),{'SkillID':str(i)},'forecast',{'Visibility':4,'RenderOpacity':1.}) for i in (1,2)]
  sample=NS(sequence=1,admission={'at':now,'cards':cards,'catalog':NS(objects=(),classes={})})
  m=Mod();m.session=object();m.monitor=NS(snapshot=lambda:sample)
  class Label:
   def __init__(self,*args):self.ready=False
   def build(self,catalog):self.ready=True
   def update(self,*args):pass
  with patch.object(ui,'DamageLabel',Label):
   m.poll_fast();self.assertEqual(len(m.labels),0)
   m.poll();m.poll();self.assertEqual(len(m.labels),2)
from skill_damage_rules_test.history import DamageHistory
class DamageHistoryTests(unittest.TestCase):
 def test_secondary_impacts_are_retained_as_separate_events_without_dereferencing(self):
  h=DamageHistory();h.next_renew=float('inf')
  events=[NS(sequence=1,arguments={'ReceivedDamages':42350.34375}),NS(sequence=2,arguments={'ReceivedDamages':42350.}),NS(sequence=3,arguments={'ReceivedDamages':float('nan')})]
  h.trace=NS(read=lambda:events)
  h.poll();self.assertEqual(list(h.events),[(1,42350.34375),(2,42350.)]);self.assertTrue(h.incomplete)
 def test_dropped_events_mark_history_incomplete(self):
  h=DamageHistory();h.trace=NS(read=lambda:[],status=lambda:NS(dropped=1,rejected=0),state='active',renew=lambda **_:None)
  h.poll();self.assertTrue(h.incomplete)

class AttackAndAffinityTests(unittest.TestCase):
 def test_basic_combo_rounds_and_caps_each_impact(self):
  c=context();c['kind']='basic';c['base_hits']=4
  c['source']['CharacterCurrentStats']=mapped({1:100,3:100000});c['target']['CurrentHP']=100000
  self.assertEqual(prediction(c)[0],Outcomes(39996,39996,39996,39996))
 def test_shot_uses_its_own_target_multiplier_and_affinity(self):
  c=context();c['kind']='aim';c['tables']['DT_Balancing_MainCharacterSkills']['Generic_FreeAim_BaseDamage']=.25
  c['target']['CharacterStats'].fields['ReceivedFreeAimDamageMultiplier']=2.
  c['affinities']=mapped({1:3})
  self.assertEqual(prediction(c)[0].failed_normal,25)
  from skill_damage_rules_test.rules import affinity_label
  self.assertEqual(affinity_label(c),'Physical: Resist x0.5')
 def test_weakness_resistance_immunity_and_absorption_are_distinct(self):
  from skill_damage_rules_test.rules import affinity_label
  for affinity,word in ((2,'Weak x1.5'),(3,'Resist x0.5'),(4,'Immune'),(5,'Absorbs')):
   c=context();c['affinities']=mapped({1:affinity})
   self.assertEqual(affinity_label(c),'Physical: '+word)
  c=context();c['target']=None
  self.assertEqual(affinity_label(c),'Select target')

class StableForecastLayoutTests(unittest.TestCase):
 def test_missing_sample_hides_without_collapsing_skill_allocation(self):
  from contextlib import nullcontext
  from skill_damage_rules_test.ui import DamageLabel
  label=DamageLabel.__new__(DamageLabel);label.kind='skill';label.native_visibility=False;label.last=None;label.label=object()
  calls=[]
  label._enum=lambda name,value:value
  label._call=lambda obj,owner,name,**args:(calls.append((name,args)) or nullcontext())
  label.update('Fail: N 10 | C 15\nPass: N 20 | C 30\nFire: Resist x0.5',4,1.)
  calls.clear();label.update('',1,0.)
  self.assertIn(('SetVisibility',{'InVisibility':2}),calls)
  self.assertFalse(any(name in ('RemoveFromParent','SetHeightOverride') for name,_ in calls))
 def test_late_observation_preserves_visible_skill_slot_without_stale_numbers(self):
  calls=[]
  owner=NS(ready=True,uncertain=False,kind='skill',last=('Fail: N 10 | C 15',4,1.),update=lambda *args:self.fail('Transient staleness must not replace the layout'),set_pending=lambda flag:calls.append(flag))
  m=Mod();m.session=object();m.monitor=NS(snapshot=lambda:None);m.labels={1:owner}
  m.last_observed_at=time.monotonic()
  m.poll_fast()
  self.assertEqual(calls,[])
  m.last_observed_at=time.monotonic()-3.
  m.poll_fast()
  self.assertEqual(calls,[True])

class NativeSkillVisibilityTests(unittest.TestCase):
 def test_page_fade_never_overrides_child_forecast_visibility(self):
  from contextlib import nullcontext
  from skill_damage_rules_test.ui import DamageLabel
  label=DamageLabel.__new__(DamageLabel);label.kind='skill';label.native_visibility=True;label.last=None;label.label=object()
  calls=[];label._enum=lambda name,value:value
  label._call=lambda obj,owner,name,**args:(calls.append((name,args)) or nullcontext())
  label.update('forecast',4,1.)
  calls.clear();label.update('forecast',4,0.);label.update('forecast',4,1.)
  self.assertEqual(calls,[])
  self.assertEqual(label.last,('forecast',4,1.))
 def test_cleanup_restores_original_description_content_before_detaching_owned_widgets(self):
  from contextlib import nullcontext
  from skill_damage_rules_test.ui import DamageLabel
  from expedition33 import _retired_tracking
  label=DamageLabel.__new__(DamageLabel);label.ready=True;label.wrapped=True
  label.parent='native root';label.original_content='original text';label.frame='forecast frame';label.label='forecast';label.planner=None;label.scope=object()
  calls=[];label._call=lambda obj,owner,name,**args:(calls.append((obj,name,args)) or nullcontext())
  with patch.object(_retired_tracking,'close_lease_only_scope',return_value=True):self.assertTrue(label.close())
  self.assertEqual(calls[0],('native root','SetContent',{'Content':'original text'}))
  self.assertEqual(calls[1:], [('forecast frame','RemoveFromParent',{}),('forecast','RemoveFromParent',{})])
  self.assertFalse(label.wrapped)

class TotalPresentationTests(unittest.TestCase):
 def test_skill_totals_and_named_procs_use_three_lines(self):
  c=context();c['source_buffs']=[NS(class_name='BP_LU_DoubleHit_C',class_index=1,index=1)]
  c['catalog']=NS(classes={},ancestors=lambda _:())
  text=predict(c)
  self.assertTrue(text.startswith('BASE DAMAGE'))
  self.assertIn('\nPASS | N ',text)
  self.assertIn('EXTRA HIT | N Unavailable',text)
  self.assertIn('TOTAL ATTACK\nINCOMPLETE',text)

class PreparedTargetingTests(unittest.TestCase):
 def test_free_aim_switches_prepared_enemy_values_without_damage_snapshot(self):
  from contextlib import nullcontext
  from expedition33 import values
  def obj(i):return NS(index=i,serial=1,address=65536+i*8)
  manager,hud,shooter,targeting,actor,a,b=map(obj,range(1,8))
  row=dict(ModeManager=manager,ModeHUD=hud,ModeShooter=shooter,ModeTargeting=targeting,ModeActor=actor,Forecasts={(a.index,a.serial,a.address):'Shot A',(b.index,b.serial,b.address):'Shot B'})
  catalog=object();row['ModeCatalog']=catalog
  calls=[];owner=NS(ready=True,kind='aim',mode_row=row,catalog=NS(with_observations=lambda _:self.fail('Widget catalog used for targeting')),update=lambda *args:calls.append(args))
  m=Mod();m.session=NS(pid=1);m.definitions=(catalog,{});m.labels={1:owner};m.last_observed_at=time.monotonic();m.mode_reader=NS(bind=lambda:nullcontext())
  def sample(target,aim=True):
   entries={manager.index:dict(IsBattleInitialized=True,HasBattleStartedEndFlow=False,CurrentCharacter=actor,CurrentHoveredCharacterFreeAim=target,SelectedAction=1),hud.index:dict(IsTargeting=not aim),shooter.index:dict(IsAiming=aim,CurrentFreeAimType=2),targeting.index:dict(LastTarget=a)}
   return ({i:NS(errors={},values={(i,k):v for k,v in fields.items()}) for i,fields in entries.items()},catalog)
  with patch.object(values,'read_values_many_with_references',side_effect=[sample(a),sample(b)]):
   m._refresh_modes();m.next_mode=0.;m._refresh_modes()
  self.assertEqual(calls,[('Shot A',4,1.),('Shot B',4,1.)])
  owner.kind='basic';row['Forecasts']={(a.index,a.serial,a.address):'Attack A'};m.next_mode=0.
  with patch.object(values,'read_values_many_with_references',return_value=sample(a,False)) as read:
   m._refresh_modes()
  self.assertIs(read.call_args.args[0],catalog)
  self.assertEqual(calls[-1],('Attack A',4,1.))
  # The collision result takes precedence over the game's sticky hover actor.
  owner.kind='aim';row['Forecasts']={(a.index,a.serial,a.address):'Shot A',(b.index,b.serial,b.address):'Shot B'}
  m.session._session=NS(_transport=NS(free_aim_region_query_protocol=1))
  m.aim_region_query=NS(manager=manager,sample=lambda _:dict(actor=(b.index,b.serial,b.address),multiplier=1.,part=(0,0,0)))
  m.next_mode=0.
  with patch.object(values,'read_values_many_with_references',return_value=sample(a)):m._refresh_modes()
  self.assertEqual(calls[-1],('Shot B',4,1.))
  m.aim_region_query.sample=lambda _:None;m.next_mode=0.
  with patch.object(values,'read_values_many_with_references',return_value=sample(a)):m._refresh_modes()
  self.assertEqual(calls[-1],('Select target',4,1.))

class ForecastReaderBindingTests(unittest.TestCase):
 def test_fast_refresh_reuses_outer_reader_operation(self):
  from expedition33._reader import _active
  from skill_damage_rules_test.mod import reader_context
  reader=NS(bind=lambda:self.fail('Nested reader bind'))
  token=_active.set(object())
  try:
   with reader_context(reader):pass
  finally:_active.reset(token)

class LiveBuffMultiplierTests(unittest.TestCase):
 def test_power_and_defense_use_live_values(self):
  c=context();c['catalog']=NS(classes={},ancestors=lambda _:())
  power=NS(class_name='BP_BattleBuff_Power_C',class_index=1,index=101)
  defense=NS(class_name='BP_BattleBuff_Defense_C',class_index=2,index=102)
  c['source_buffs']=(power,);c['target_buffs']=(defense,)
  c['extras']={101:{'DamageMultiplier':1.25},102:{'DamageReceivedMultiplier':1.5}}
  self.assertEqual(prediction(c)[0].failed_normal,188)

class GradientAttackTests(unittest.TestCase):
 def test_striker_two_inputs_and_sabotage_single_input(self):
  for name,coefficient,qte in (('Striker',10.,(2,)),('Sabotage',3.,(1,))):
   c=context();c['skill']={'NameID':name,'SkillScript':NS(asset='BP_Battle_SkillScript_Verso_'+name+'_C')}
   c['tables']['DT_Balancing_MainCharacterSkills'][name+'_BaseDamage']=coefficient;c['qte_per_hit']=qte
   out,_=prediction(c);self.assertEqual(out.failed_normal,int(100*coefficient));self.assertEqual(out.passed_normal,round(100*coefficient*(1+.1*qte[0])))
 def test_angels_eyes_counts_eight_damaging_impacts_excluding_aureole_event(self):
  c=context();c['skill']={'NameID':'AngelsEyes','SkillScript':NS(asset='BP_Battle_SkillScript_Verso_AngelsEyes_C')}
  c['tables']['DT_Balancing_MainCharacterSkills']['AngelsEyes_BaseDamage']=1.;c['qte_per_hit']=(1,)*8
  out,procs=prediction(c);self.assertEqual(out.failed_normal,800);self.assertEqual(out.passed_normal,960);self.assertIn('Aureole',procs)

class SafeConstructionTests(unittest.TestCase):
 def test_size_box_dimensions_use_individual_calls_without_marking_unknown(self):
  from skill_damage_rules_test.ui import DamageLabel
  from contextlib import nullcontext
  label=DamageLabel.__new__(DamageLabel);label.scope=NS(_session=object());label.uncertain=False
  called=[];label._call=lambda *args,**kwargs:(called.append(args[2]) or nullcontext())
  with patch('expedition33._ui_batch.invoke_setters') as batch:
   label._setters(((object(),'SizeBox','SetHeightOverride',{'InHeightOverride':56.}),(object(),'SizeBox','SetWidthOverride',{'InWidthOverride':600.})))
   batch.assert_not_called()
  self.assertFalse(label.uncertain);self.assertEqual(called,['SetHeightOverride','SetWidthOverride'])

 def test_local_batch_rejection_does_not_block_owned_cleanup(self):
  from skill_damage_rules_test.ui import DamageLabel
  for aborted in (False,True):
   label=DamageLabel.__new__(DamageLabel);label.scope=NS(_session=NS(_transport=NS(_closed=aborted)));label.uncertain=False
   label.planner=NS(prepare=lambda *args,**kwargs:object());label._function=lambda *args:object()
   with patch('expedition33._ui_batch.extended_layout_available',return_value=True),patch('expedition33._ui_batch.invoke_setters',side_effect=ValueError('rejected')):
    with self.assertRaises(ValueError):label._setters(((object(),'Widget','SetVisibility',{}),))
   self.assertEqual(label.uncertain,aborted)

class FollowupForecastTests(unittest.TestCase):
 def test_delayed_repeats_use_latest_hit_not_every_hit(self):
  from skill_damage_rules_test.rules import repeat_plans
  times=(.2666667,.3333333,.4666667,.5833333,.7166667,.8,.9666667,1.5833333)
  plans=repeat_plans(times,.25,jitter=0)
  self.assertEqual(plans,((2,5,6,7),))
 def test_recorded_angels_eyes_total_is_inside_timing_range_with_rounding_tolerance(self):
  from skill_damage_rules_test.rules import followup_bounds
  from skill_damage_rules_test.forecast import Hit
  c=context();c['source_buffs']=(NS(class_name='BP_LU_DoubleHit_C',index=1),)
  c['extras']={1:{'Time Offset':.25}}
  c['impact_seconds']=(.2666667,.3333333,.4666667,.5833333,.7166667,.8,.9666667,1.5833333)
  failed=[Hit(11583,1,0,final_multiplier=8.7890625*(2 if i in (2,5) else 1),additive_percent=.55) for i in range(8)]
  passed=[Hit(11583,1.2,0,final_multiplier=h.final_multiplier,additive_percent=.55) for h in failed]
  low,high=followup_bounds(c,failed,passed)
  direct=sum(h.damage(True) for h in passed)
  self.assertLessEqual(direct+low[3],4544518)
  self.assertGreaterEqual(direct+high[3]+12,4544518)
  self.assertEqual(direct,2840322)
 def test_recorded_frenzy_angels_eyes_includes_growth_and_delayed_repeats(self):
  from skill_damage_rules_test.rules import followup_bounds
  from skill_damage_rules_test.forecast import Hit
  c=context();c['source_buffs']=(NS(class_name='BP_LU_DoubleHit_C',index=1),)
  c['extras']={1:{'Time Offset':.25}}
  c['impact_seconds']=(0.,.079,.219,.329,.469,.547,.719,1.485)
  # Observed first critical 672354.057; audited Frenzy x1.1 each impact,
  # Double Third on 3/6. Repeated hits copy the latest already-scaled hit.
  passed=[Hit(672354.057/1.5,1.,0,final_multiplier=1.1**i*(2 if i in (2,5) else 1)) for i in range(8)]
  low,high=followup_bounds(c,passed,passed)
  direct=sum(h.damage(True) for h in passed)
  actual=15879454.106
  self.assertLessEqual(direct+low[3]-12,actual)
  self.assertGreaterEqual(direct+high[3]+12,actual)
 def test_single_skill_shows_extra_and_combined_totals(self):
  c=context();c['catalog']=NS(classes={},ancestors=lambda _:())
  c['source_buffs']=(NS(class_name='BP_LU_DoubleHit_C',class_index=1,index=10),)
  c['extras']={10:{'Time Offset':.25}};c['impact_seconds']=(1.,)
  text=predict(c)
  self.assertIn('EXTRA HIT | N 100-110 | C 150-165',text)
  self.assertIn('TOTAL ATTACK\nFAIL | N 200 | C 300\nPASS | N 220 | C 330',text)
  self.assertEqual(len(text.splitlines()),8)
 def test_missing_delay_does_not_claim_complete_total(self):
  c=context();c['catalog']=NS(classes={},ancestors=lambda _:())
  c['source_buffs']=(NS(class_name='BP_LU_DoubleHit_C',class_index=1,index=10),)
  self.assertIn('TOTAL ATTACK\nINCOMPLETE',predict(c))


class AugmentedAimTests(unittest.TestCase):
 def test_augmented_aim_is_reviewed_but_only_changes_free_aim(self):
  c=context();c['catalog']=NS(classes={1:NS(name='BP_LU_FreeAimDamage+25_C')},ancestors=lambda _: (1,))
  c['callback_owners']={'ProcessDealtRawDamages':{'BP_LU_FreeAimDamage+25_C'}}
  original=prediction(c)[0]
  c['source_buffs']=(NS(class_name='BP_LU_FreeAimDamage+25_C',class_index=1,index=99),)
  self.assertEqual(prediction(c)[0],original)
  c['kind']='aim';c['tables']['DT_Balancing_MainCharacterSkills']['Generic_FreeAim_BaseDamage']=1.
  c['target']['CharacterStats'].fields['ReceivedFreeAimDamageMultiplier']=1.
  c['tables']['DT_Balancing_Luminas']['AugmentedAim_DamageIncrease']=.25
  self.assertEqual(prediction(c)[0],Outcomes(125,188,125,188))
 def test_augmented_attack_only_changes_basic_attack(self):
  c=context();c['catalog']=NS(classes={1:NS(name='BP_LU_BaseAttack+25_C')},ancestors=lambda _: (1,))
  c['callback_owners']={'ProcessDealtRawDamages':{'BP_LU_BaseAttack+25_C'}}
  original=prediction(c)[0];c['source_buffs']=(NS(class_name='BP_LU_BaseAttack+25_C',class_index=1,index=99),)
  self.assertEqual(prediction(c)[0],original)
  c['kind']='basic';c['base_hits']=1;c['tables']['DT_Balancing_Luminas']['AugmentedAttack_DamageIncrease']=.25
  self.assertEqual(prediction(c)[0],Outcomes(125,188,125,188))

class ReviewedLoadoutTests(unittest.TestCase):
 def make(self,names):
  c=context();c['catalog']=NS(classes={i:NS(name=n)for i,n in enumerate(names)},ancestors=lambda i:(i,))
  c['source_buffs']=tuple(NS(class_name=n,class_index=i,index=i)for i,n in enumerate(names))
  c['callback_owners']={'ProcessDealtRawDamages':set(names)}
  return c
 def test_low_hp_and_warming_use_live_base_hp_and_stack_count(self):
  c=self.make(('BP_LU_LastStand_C','BP_LU_Warming_C'));c['source']['CharacterBaseStats']=mapped({1:1000});c['source']['CurrentHP']=100
  c['extras']={1:{'WarmingBuffStackCount':2}};c['tables']['DT_Balancing_Luminas']['Warming_DamageIncreasePerStack']=.05
  self.assertEqual(prediction(c)[0].failed_normal,165)
  c['source']['CurrentHP']=101;self.assertEqual(prediction(c)[0].failed_normal,110)
 def test_tainted_counts_distinct_status_classes_not_stacks(self):
  c=self.make(('BP_LU_Tainted_C','StatusA','StatusB'));c['source_buffs']+= (NS(class_name='StatusA',class_index=1,index=3),)
  c['callback_owners']={'ProcessDealtRawDamages':{'BP_LU_Tainted_C'}};c['extras']={0:{'Type':0},1:{'Type':2},2:{'Type':2},3:{'Type':2}};c['tables']['DT_Balancing_Luminas']['Tainted_DamageIncreasePerStatusEffect']=.15
  self.assertEqual(prediction(c)[0].failed_normal,130)
 def test_piercing_shot_ignores_shields_only_for_aim(self):
  c=self.make(('BP_LU_PiercingShot_C',));c['target']['CurrentShieldPoints']=1
  self.assertEqual(prediction(c)[0].failed_normal,0)
  c['kind']='aim';c['target']['CharacterStats'].fields['ReceivedFreeAimDamageMultiplier']=1.
  c['tables']['DT_Balancing_MainCharacterSkills']['Generic_FreeAim_BaseDamage']=1.;c['tables']['DT_Balancing_Luminas']['PiercingShot_DamageIncrease']=.25
  self.assertEqual(prediction(c)[0].failed_normal,125)
 def test_frenzy_follows_authored_impact_groups_and_existing_counter(self):
  c=self.make(('BP_LU_Frenzy_C',));c['extras']={0:{'HitCounter':0}};c['impact_seconds']=(0.,)
  c['tables']['DT_Balancing_Luminas']['Frenzy_DamageMultiplierPerHit']=1.1
  self.assertEqual(prediction(c)[0].failed_normal,100)
  c['extras'][0]['HitCounter']=2;self.assertEqual(prediction(c)[0].failed_normal,121)
  # Angel's Eyes remains normal skill damage even in a Gradient card tree.
  c['gradient']=True;c['skill']['NameID']='AngelsEyes';c['skill']['SkillScript']=NS(asset='BP_Battle_SkillScript_Verso_AngelsEyes_C')
  c['qte_per_hit']=(0,)*8;c['impact_seconds']=tuple(range(8))
  c['tables']['DT_Balancing_MainCharacterSkills']['AngelsEyes_BaseDamage']=1.
  audit={};prediction(c,audit=audit)
  values=[h['final_multiplier'] for h in audit['failed']]
  self.assertEqual(len(values),8)
  for i,value in enumerate(values):self.assertAlmostEqual(value/values[0],1.1**i)
 def test_versatile_only_applies_after_live_shot_flag_to_basic(self):
  c=self.make(('BP_LU_Versatile_C',));c['extras']={0:{'BaseAttackDamageBonus':True}};c['tables']['DT_Balancing_Luminas']['Versatile_DamageIncrease']=.5
  self.assertEqual(prediction(c)[0].failed_normal,100)
  c['kind']='basic';c['base_hits']=1;self.assertEqual(prediction(c)[0].failed_normal,150)
 def test_gradient_bonus_is_scoped_to_gradient(self):
  c=self.make(('BP_LU_GradientFighter_C',));c['tables']['DT_Balancing_Luminas']['GradientFighter_IncreasedDamage']=.25
  c['extras']={0:{'GradientDamageIncrease':0.}}
  self.assertEqual(prediction(c)[0].failed_normal,100)
  c['gradient']=True;self.assertEqual(prediction(c)[0].failed_normal,125)
 def test_gradient_fighter_retained_state_applies_to_post_revival_shots_and_basic(self):
  for kind in ('aim','basic','skill'):
   c=self.make(('BP_LU_GradientFighter_C',));c['kind']=kind;c['base_hits']=1
   c['target']['CharacterStats'].fields['ReceivedFreeAimDamageMultiplier']=1.
   c['tables']['DT_Balancing_MainCharacterSkills']['Generic_FreeAim_BaseDamage']=1.
   c['extras']={0:{'GradientDamageIncrease':0.}}
   self.assertEqual(prediction(c)[0].failed_normal,100)
   c['extras'][0]['GradientDamageIncrease']=.25
   self.assertEqual(prediction(c)[0].failed_normal,125)
   c['extras'][0]['GradientDamageIncrease']=.5
   self.assertEqual(prediction(c)[0].failed_normal,100)
   c['extras']={}
   with self.assertRaises(ValueError):prediction(c)
 def test_powerful_mark_never_silently_guesses_activation_timing(self):
  c=self.make(('BP_LU_PowerfulMark_C',));self.assertEqual(prediction(c)[0].failed_normal,100)
  c['target_buffs']=(NS(class_name='BP_BattleBuff_Marked_C',class_index=0,index=5),)
  with self.assertRaisesRegex(ValueError,'Powerful Mark activation'):prediction(c)


class ModeConstructionPriorityTests(unittest.TestCase):
 def test_attack_and_aim_attach_before_offscreen_skills(self):
  from skill_damage_rules_test import ui
  now=time.monotonic();built=[]
  cards=[(NS(index=i,serial=1,address=65536+i*8),{'SkillID':kind,'Kind':kind},'forecast',{'Visibility':4,'RenderOpacity':1.})for i,kind in enumerate(('skill','basic','aim'),1)]
  snapshot=NS(sequence=1,admission={'at':now,'cards':cards,'catalog':NS(objects=(),classes={})})
  m=Mod();m.session=object();m.monitor=NS(snapshot=lambda:snapshot)
  class Label:
   def __init__(self,session,card,row,*args):self.ready=False;self.kind=row['Kind']
   def build(self,catalog):self.ready=True;built.append(self.kind)
   def update(self,*args):pass
  with patch.object(ui,'DamageLabel',Label):
   m._poll_data();m._poll_data();m._poll_data()
  self.assertEqual(built,['basic','aim','skill'])

class MarkDamageTests(unittest.TestCase):
 def marked(self,count=1):
  c=context();c['catalog']=NS(classes={1:NS(name='BP_BattleBuff_Marked_C')},ancestors=lambda _:(1,))
  c['target_buffs']=(NS(class_name='BP_BattleBuff_Marked_C',class_index=1,index=7),)
  c['callback_owners']={'ProcessReceivedFinalDamages':{'BP_BattleBuff_Marked_C'}}
  c['extras']={7:dict(HitCountToRemoveMark=count,ModifyDamageElements=False,IsMarkedForRemoval=False)}
  return c
 def test_live_mark_counter_affects_only_remaining_impacts(self):
  c=self.marked();c['kind']='basic';c['base_hits']=2;audit={}
  self.assertEqual(prediction(c,audit=audit)[0],Outcomes(125,188,125,188))
  self.assertEqual(audit['mark']['affected_hits'],1)
  c['extras'][7]['HitCountToRemoveMark']=2
  self.assertEqual(prediction(c)[0],Outcomes(150,226,150,226))
 def test_mark_removal_and_reapplication_refresh_the_same_forecast(self):
  c=self.marked();self.assertEqual(prediction(c)[0].failed_normal,150)
  c['extras'][7]['IsMarkedForRemoval']=True;self.assertEqual(prediction(c)[0].failed_normal,100)
  c['extras'][7]['IsMarkedForRemoval']=False;self.assertEqual(prediction(c)[0].failed_normal,150)
  self.assertIn('Mark x1.5',predict(c))
 def test_mark_element_override_is_not_silently_ignored(self):
  c=self.marked();c['extras'][7]['ModifyDamageElements']=True
  with self.assertRaisesRegex(ValueError,'element replacement'):prediction(c)
