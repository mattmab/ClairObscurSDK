"""Bounded, explicit skill and optional meter policy; no authored defaults."""
import math,re,struct
from ._character_skill_schema import INPUTS,ROLES,DYNAMIC
SIZE=16276
METER_INPUTS=(19,20,21,22,30,75,77)
NUMBERS=('distance','initiative','damage','breaking','qte_bonus','charged_multiplier','final_multiplier','heal_threshold','heal_fraction','recovery_fraction')
INTS=('flags','element','buff','duration','cleanse_kind','damage_reason','buff_reason')
def active(i,count,meter):return (i not in METER_INPUTS or meter) and (not 38<=i<74 or (i-38)//4<count)
def path(value,kind):
 if type(value)is not str or len(value)>=320 or re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.[A-Za-z0-9_]+(?::[A-Za-z0-9_]+)?',value)is None:raise ValueError('Canonical skill dependency required')
 asset,sep,method=value.partition(':');pkg,leaf=asset.rsplit('.',1)
 if len(pkg)>=256 or len(leaf)>=96 or len(method)>=96:raise ValueError('Skill dependency component too long')
 if bool(sep)!=(kind=='function') or leaf!=pkg.rsplit('/',1)[1]+('_C' if kind in ('class','function') else ''):raise ValueError('Skill dependency kind mismatch')
 return value.encode('ascii').ljust(320,b'\0')
def encode(profile):
 if type(profile)is not dict or set(profile)!={'paths','skills','meter'}:raise ValueError('Explicit skill profile required')
 skills=profile['skills'];meter=profile['meter'];paths=profile['paths']
 if type(skills)not in (tuple,list) or not 1<=len(skills)<=9:raise ValueError('One to nine skill rules required')
 if type(meter)is not dict or set(meter)!={'enabled','increment','cap','reset','buff_mask','own_only','reason_mask'} or type(meter['enabled'])is not bool or type(meter['own_only'])is not bool:raise ValueError('Explicit meter policy required')
 enabled=meter['enabled']
 for key in ('increment','cap','reset','buff_mask','reason_mask'):
  if type(meter[key])is not int:raise ValueError('Meter integer required')
 if enabled:
  if not 1<=meter['increment']<=meter['cap']<=10000 or not 0<=meter['reset']<=meter['cap'] or not 1<=meter['buff_mask']<=127 or not 0<meter['reason_mask']<2**64:raise ValueError('Invalid meter bounds')
 elif any(meter[k] for k in meter if k!='enabled'):raise ValueError('Disabled meter fields must be empty')
 required={INPUTS[i]['role'] for i in DYNAMIC if active(i,len(skills),enabled)}
 if type(paths)is not dict or set(paths)!=required:raise ValueError('Exact active skill dependencies required')
 out=bytearray()
 for i in DYNAMIC:out+=path(paths[INPUTS[i]['role']],INPUTS[i]['kind']) if active(i,len(skills),enabled) else bytes(320)
 out+=struct.pack('<7IQ',len(skills),enabled,meter['increment'],meter['cap'],meter['reset'],meter['buff_mask'],meter['own_only'],meter['reason_mask'])
 for rule in skills:
  if type(rule)is not dict or set(rule)!={*INTS,*NUMBERS,'debug_reason'}:raise ValueError('Complete skill rule required')
  if any(type(rule[k])is not int for k in INTS):raise ValueError('Skill integer required')
  if not 0<=rule['flags']<=2047 or not 0<=rule['element']<=256 or not -1<=rule['buff']<=6 or not 0<=rule['duration']<=999 or any(not 0<=rule[k]<=255 for k in ('cleanse_kind','damage_reason','buff_reason')):raise ValueError('Skill integer outside bounds')
  nums=tuple(rule[k] for k in NUMBERS)
  if any(type(x)not in (int,float) or not math.isfinite(x) or x<0 or x>1e4 for x in nums) or any(rule[k]>1 for k in ('heal_threshold','heal_fraction','recovery_fraction')):raise ValueError('Invalid skill numeric value')
  reason=rule['debug_reason']
  if type(reason)is not str or re.fullmatch('[A-Za-z0-9_]{1,63}',reason)is None:raise ValueError('Bounded skill debug ID required')
  out+=struct.pack('<IIii4I10d',*(rule[k] for k in INTS),0,*nums)+reason.encode('utf-16-le').ljust(128,b'\0')
 return bytes(out).ljust(SIZE,b'\0')
def decode(data):
 if type(data)is not bytes or len(data)!=SIZE:raise ValueError('Skill profile size')
 n,enabled,increment,cap,reset,buffs,own,reasons=struct.unpack_from('<7IQ',data,14080)
 if not 1<=n<=9 or enabled>1 or own>1:raise ValueError('Skill count or meter flags')
 p=dict(paths={},skills=[],meter=dict(enabled=bool(enabled),increment=increment,cap=cap,reset=reset,buff_mask=buffs,own_only=bool(own),reason_mask=reasons))
 for k,i in enumerate(DYNAMIC):
  raw=data[k*320:(k+1)*320]
  if active(i,n,enabled):
   end=raw.find(b'\0')
   if end<1 or any(raw[end:]):raise ValueError('Skill path padding')
   p['paths'][INPUTS[i]['role']]=raw[:end].decode('ascii')
  elif any(raw):raise ValueError('Inactive skill dependency')
 for i in range(n):
  at=14116+i*240;values=struct.unpack_from('<IIii4I10d',data,at)
  rule=dict(zip(INTS,values[:7]));rule.update(zip(NUMBERS,values[8:]));raw=data[at+112:at+240].decode('utf-16-le');rule['debug_reason']=raw.split('\0')[0];p['skills'].append(rule)
 if encode(p)!=data:raise ValueError('Skill profile flags or unused slots')
 return p
def inputs(profile):
 p=decode(encode(profile));n=len(p['skills']);enabled=p['meter']['enabled']
 return tuple(dict(row,path=p['paths'][row['role']]) if i in DYNAMIC and active(i,n,enabled) else (dict(row) if active(i,n,enabled) else None) for i,row in enumerate(INPUTS))
