import sys,types,unittest,struct,copy
from pathlib import Path
from types import SimpleNamespace as NS
from dataclasses import asdict
from expedition33 import RuntimeQueryError
from expedition33._free_aim_region import encode,decode,validate_request,SIZE,OUTPUT
pkg=types.ModuleType('aim_region_test');pkg.__path__=[str(Path('mods/SkillDamage').resolve())];sys.modules[pkg.__name__]=pkg
from aim_region_test.forecast import Hit
from aim_region_test.aim_region import apply_region,text_for_region,ScriptedRegions

def obj(i):return NS(index=i,serial=100+i,address=0x10000+i*8)
def request():return encode(obj(1),55,obj(2),tuple(obj(i) for i in range(3,10)),123)
def model(hit,hp=100000):
    row=asdict(hit);row['damage_limit']=None
    return dict(failed_normal=min(hp,hit.damage(False)),failed_critical=min(hp,hit.damage(True)),passed_normal=min(hp,hit.damage(False)),passed_critical=min(hp,hit.damage(True)),
        inputs=dict(target_hp=hp,failed=[row],passed=[copy.deepcopy(row)],extra_lower=(0,)*4,extra_upper=(0,)*4))
def region(factor,part_type=1):return dict(multiplier=factor,body_part=part_type,actor=(1,2,65536),component=(3,4,65544),part=(5,6,65552),base_damage=.4)

class AimRegionTests(unittest.TestCase):
    def test_self_hit_uses_enemy_stats_not_shooters_attack_or_critical(self):
        from unittest.mock import patch
        from aim_region_test import observe
        actor=NS(index=1,class_index=10);part=NS(index=5,name='BP_FreeAimTargetPart')
        stats=NS(index=7);buffs=NS(index=8)
        catalog=NS(by_index={1:actor,5:part},classes={10:NS(name='BP_EnemyBattle_Bruler_C')},ancestors=lambda _: (10,))
        values=[{1:{'AC_jRPG_CharacterStats':stats,'ElementalAffinitiesCurrent':NS(items={1:1})}},
                {7:{'CharacterCurrentStats':NS(items={1:1623.,3:233.,6:0.}), 'CurrentHP':1623.,'CurrentShieldPoints':0,'BattleBuffComponent':buffs}},
                {8:{'ActiveBattleBuffs':NS(items=())}}]
        def read(*args,**kwargs):return values.pop(0),catalog
        with patch('expedition33.catalog.capture_selected',return_value=catalog),patch('expedition33.values.read_values_many_with_references',side_effect=read),patch.object(observe,'fields',side_effect=lambda value:value):
            result=ScriptedRegions(1).resolve(region(0,0))
        self.assertEqual(result['scripted_damage'],720)
        result=apply_region(model(Hit(999999,1,0),hp=1623),result)
        self.assertEqual(tuple(result[k] for k in ('failed_normal','failed_critical','passed_normal','passed_critical')),(720,)*4)

    def test_callback_family_follows_blueprint_inheritance(self):
        classes={1:NS(name='BP_CustomPortier_C'),2:NS(name='BP_EnemyBattle_Portier_C')}
        catalog=NS(classes=classes,ancestors=lambda _: (1,2))
        self.assertEqual(ScriptedRegions.rule_for(catalog,NS(class_index=1)),
                         ('percent_hp','SM_Abbest_FreeAimSelfDamage',None))
        self.assertEqual(ScriptedRegions.RULES['BP_EnemyBattle_Portier_C'],
                         ScriptedRegions.RULES['BP_EnemyBattle_SpringMeadowElementalGrunt_C'])
        self.assertEqual(ScriptedRegions.RULES['BP_EnemyBattle_Bruler_C'],('self_hit',.3,None))

    def test_unresolved_scripted_region_does_not_display_zero_shot(self):
        r=dict(region(0,0),scripted_unknown=True)
        self.assertIsNone(apply_region(model(Hit(100,1,0)),r))
        self.assertEqual(text_for_region('Shot N 0',None,r),'Special weak spot: damage rule not yet resolved')

    def test_scripted_percent_damage_replaces_normal_and_critical_outcomes(self):
        body=model(Hit(100,1,500),hp=1256)
        scripted=dict(region(0,0),scripted_damage=628,scripted_percent=.5,scripted_rule='Lancelier orb')
        result=apply_region(body,scripted)
        self.assertEqual(tuple(result[k] for k in ('failed_normal','failed_critical','passed_normal','passed_critical')),(628,)*4)
        self.assertEqual(result['inputs']['direct_upper'],(628,)*4)
        self.assertIn('50% max HP',text_for_region('old body damage',result,scripted))
        self.assertNotIn('old body damage',text_for_region('old body damage',result,scripted))
    def test_weak_spot_changes_attack_coefficient_before_defense(self):
        original=model(Hit(100,.4,100));before=copy.deepcopy(original)
        weak=apply_region(original,region(5.5))
        expected=Hit(100,.4*5.5,100)
        self.assertEqual((weak['failed_normal'],weak['failed_critical']),(expected.damage(False),expected.damage(True)))
        self.assertNotEqual(weak['failed_normal'],round(original['failed_normal']*5.5))
        self.assertEqual(original,before)

    def test_region_recomputes_raw_hit_instead_of_multiplying_hp_capped_total(self):
        body=model(Hit(100,10,0),hp=50)
        weak=apply_region(body,region(.01))
        self.assertEqual((weak['failed_normal'],weak['failed_critical']),(10,15))

    def test_roulette_range_and_zero_damage_regions_preserved(self):
        body=model(Hit(100,1,0,final_multiplier=.5,upper_multiplier=4))
        weak=apply_region(body,region(5.5))
        self.assertEqual((weak['failed_normal'],weak['inputs']['direct_upper'][0]),(275,1100))
        text=text_for_region('Shot (body)\nPhysical: Neutral',weak,region(5.5))
        self.assertIn('Weak spot x5.5',text);self.assertIn('275-1,100',text)
        self.assertEqual(apply_region(body,region(0))['failed_critical'],0)

    def test_scripted_target_is_not_falsely_reported_as_regular_shot_damage(self):
        r=region(10,3);self.assertIsNone(apply_region(model(Hit(100,1,0)),r))
        self.assertEqual(text_for_region('',None,r),'Special weak spot: enemy-specific effect')

    def test_wire_request_has_no_output_or_unowned_identity_bytes(self):
        sent=request();validate_request(sent)
        for offset in (176,255,256,SIZE-1):
            bad=bytearray(sent);bad[offset]=1
            with self.assertRaises(ValueError):validate_request(bytes(bad))

    def test_wire_reply_is_correlated_and_has_detached_part_identities(self):
        sent=request();raw=bytearray(sent);struct.pack_into('<II',raw,8,0,1)
        OUTPUT.pack_into(raw,256,1,1,20,21,0x30000,22,23,0x30008,24,25,0x30010,5.5,.4)
        r=decode(sent,bytes(raw));self.assertEqual(r['multiplier'],5.5);self.assertEqual(r['part'],(24,25,0x30010))
        raw[24]^=1
        with self.assertRaises(RuntimeQueryError):decode(sent,bytes(raw))

    def test_empty_trace_does_not_reuse_previous_part(self):
        sent=request();raw=bytearray(sent);struct.pack_into('<II',raw,8,0,1)
        self.assertIsNone(decode(sent,bytes(raw)))

if __name__=='__main__':unittest.main()
