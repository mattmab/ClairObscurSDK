from expedition33._character_skill_schema import INPUTS,DYNAMIC
from expedition33._character_skill_config import active
def profile(count=9,meter=True,character='TestScholar'):
 paths={}
 for i in DYNAMIC:
  if not active(i,count,meter):continue
  row=INPUTS[i];name=character+'_'+row['role'];package='/Game/SDK/Sample/'+name
  paths[row['role']]=package+'.'+name+('_C:Callback' if row['kind']=='function' else '_C' if row['kind']=='class' else '')
 rule=dict(flags=1|4|8|32,element=256,buff=-1,duration=0,cleanse_kind=0,damage_reason=1,buff_reason=4,distance=150.,initiative=500.,damage=2.,breaking=.5,qte_bonus=.25,charged_multiplier=1.5,final_multiplier=3.,heal_threshold=0.,heal_fraction=0.,recovery_fraction=0.,debug_reason='SampleSkill')
 policy=dict(enabled=meter,increment=7 if meter else 0,cap=30 if meter else 0,reset=0,buff_mask=5 if meter else 0,own_only=meter,reason_mask=1<<3 if meter else 0)
 return dict(paths=paths,skills=[dict(rule,debug_reason=f'SampleSkill{i}') for i in range(count)],meter=policy)
PROFILE=profile()
