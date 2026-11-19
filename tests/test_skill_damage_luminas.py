import sys,types,unittest,copy
from pathlib import Path
from types import SimpleNamespace as NS
pkg=types.ModuleType('all_luminas_test');pkg.__path__=[str(Path('mods/SkillDamage').resolve())];sys.modules[pkg.__name__]=pkg
from all_luminas_test.luminas import LiveLuminas,display_name
from all_luminas_test.forecast import Hit,Outcomes
from all_luminas_test.presentation import skill_panel,visible_rows
from all_luminas_test.bar_projection import loss_range

def context(*names):
    return dict(source_buffs=tuple(NS(class_name='BP_LU_'+n+'_C',index=i) for i,n in enumerate(names)),target_buffs=(),
        source={'CurrentHP':100,'CurrentShieldPoints':0,'CharacterCurrentStats':NS(items={1:100})},extras={},party_count=1,
        tables={'DT_Balancing_Luminas':dict(AlternatingCritical_DamageIncrease=.5,Immaculate_DamageIncrease=.3,
            FirstOffensive_DamageMultiplierDealtValue=1.5,Roulette_LowValue=.5,Roulette_HighValue=2.,
            ShieldAffinity_DamageIncrease=.3,PowerfulShield_DamageIncreasePerShield=.1,
            PowerDodgeCombo_DamageIncrease=.1,ReinforcementParade_DamageIncreasePerParry=.2)})

class AllLuminaTests(unittest.TestCase):
    def test_large_buff_stack_reads_all_effects_in_bounded_batches(self):
        from all_luminas_test.observe import read_bounded
        from unittest.mock import patch
        objects=[NS(index=i,serial=1,address=65536+i*8) for i in range(600)]
        batches=[]
        def read(c,objs,fields):
            batches.append((c,len(objs)))
            return {o.index:NS(errors={},values={('',fields[0]):o.index}) for o in objs},c+1
        with patch('all_luminas_test.observe.read_values_many_with_references',side_effect=read):
            rows,c=read_bounded(0,objects+objects[:10],('BattleBuffInstance',))
        self.assertEqual(batches,[(0,256),(1,256),(2,88)])
        self.assertEqual(len(rows),600);self.assertEqual(rows[599]['BattleBuffInstance'],599);self.assertEqual(c,3)

    def test_alternating_critical_consumes_only_first_noncritical_impact_without_mutating_live_state(self):
        c=context('AlternatingCritical');c['extras'][0]={'DamageIncrease':True};before=copy.deepcopy(c['extras'])
        luminas=LiveLuminas(c)
        self.assertEqual(luminas.impact(0),(0.5,1.))
        self.assertEqual(luminas.impact(1),(0.,1.))
        self.assertEqual(luminas.impact(0,critical=True),(0.,1.))
        self.assertEqual(luminas.impact(0),(0.5,1.))
        self.assertEqual(c['extras'],before)
        c['extras'][0]['DamageIncrease']=False
        self.assertEqual(LiveLuminas(c).impact(0),(0.,1.))

    def test_first_offensive_and_immaculate_use_distinct_observed_flags(self):
        c=context('FirstOffensive','Immaculate');c['extras']={0:{'FirstDamageDealt':False},1:{'HasReceiveDamages':False}}
        live=LiveLuminas(c)
        self.assertEqual(live.impact(0),(.3,1.5));self.assertEqual(live.impact(1),(.3,1.))
        c['extras']={0:{'FirstDamageDealt':True},1:{'HasReceiveDamages':True}}
        self.assertEqual(LiveLuminas(c).impact(0),(0.,1.))

    def test_roulette_is_full_authored_range_not_mean_and_does_not_roll_rng(self):
        c=context('Roulette');live=LiveLuminas(c)
        self.assertEqual(live.impact(0),(0.,.5));self.assertEqual(live.impact(0,upper=True),(0.,2.))
        hit=Hit(100,1,0,final_multiplier=.5,upper_multiplier=4)
        self.assertEqual((hit.damage(False),hit.damage(False,upper=True)),(50,200))
        self.assertEqual((hit.damage(True),hit.damage(True,upper=True)),(75,300))
        capped=Hit(100,1,0,final_multiplier=.5,upper_multiplier=4,damage_limit=80)
        self.assertEqual(capped.damage(True,upper=True),80)

    def test_critical_and_normal_additive_bonuses_are_separate(self):
        hit=Hit(100,1,0,additive_percent=1.,critical_additive_percent=-.5)
        self.assertEqual(hit.damage(False),200);self.assertEqual(hit.damage(True),225)

    def test_shields_and_reactive_counters_are_character_local(self):
        c=context('IDontNeedShield','PowerfulShield','PowerDodgeCombo','ReinforcementParade')
        c['source']['CurrentShieldPoints']=3;c['extras']={2:{'AmountOfDodge':2},3:{'ParrySuccessCount':4}}
        self.assertAlmostEqual(LiveLuminas(c).impact(0)[0],1.6)
        c['source']['CurrentShieldPoints']=0;c['extras'][2]['AmountOfDodge']=0;c['extras'][3]['ParrySuccessCount']=0
        self.assertEqual(LiveLuminas(c).impact(0),(0.,1.))

    def test_teamwork_requires_multiple_living_allies_and_no_dead_party(self):
        c=context('Teamwork');self.assertEqual(LiveLuminas(c).impact(0),(0.,1.))
        c.update(party_count=3,dead_party_count=0)
        self.assertEqual(LiveLuminas(c).impact(0),(0.,1.1))
        c['dead_party_count']=1;self.assertEqual(LiveLuminas(c).impact(0),(0.,1.))
        del c['dead_party_count']
        with self.assertRaisesRegex(ValueError,'party state'):LiveLuminas(c).impact(0)

    def test_counter_and_jump_damage_are_not_applied_to_unrelated_attack_reasons(self):
        c=context('EmpoweringJumps','CounterDamage+50');self.assertEqual(LiveLuminas(c).impact(0),(0.,1.))

    def test_missing_state_is_not_silently_zero_and_message_has_no_class_identifier(self):
        with self.assertRaisesRegex(ValueError,'Reading Alternating Critical combat state'):LiveLuminas(context('AlternatingCritical'))
        self.assertEqual(display_name('BP_LU_AlternatingCritical_C'),'Alternating Critical')

    def test_random_bounds_reach_collapsed_totals_and_health_bar(self):
        values=Outcomes(50,75,60,90);audit=dict(direct_upper=(200,300,240,360),extra_lower=(10,15,12,18),extra_upper=(40,60,48,72))
        rows=visible_rows(skill_panel(values,audit,('extra hit',),'Physical: Neutral',1000).damage_rows)
        total=next(r for r in rows if r.kind=='total_fail')
        self.assertEqual((total.normal,total.critical),('60-240','90-360'))
        self.assertEqual(loss_range(dict(failed_normal=50,failed_critical=75,passed_normal=60,passed_critical=90,inputs=audit),1000),(60,432))

if __name__=='__main__':unittest.main()
