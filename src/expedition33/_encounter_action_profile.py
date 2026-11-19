"""Explicit parameters for an owned vanilla TriggerBattle action."""
import re,struct
CONFIG=240;END=1652;PARTY_CAPACITY=6
FIELDS={'table':276,'row':628,'music':724}

def asset_parts(value):
 if type(value)is not str or re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.\1',value) is None:
  raise ValueError('Canonical game asset path required')
 package,asset=value.split('.')
 if len(package)>=256 or len(asset)>=96:raise ValueError('Encounter asset path bounds')
 return package,asset

def identifier(value):
 if type(value)is not str or re.fullmatch(r'[A-Za-z0-9_]{1,95}',value) is None:raise ValueError('Encounter row or party ID')
 return value

def validate_profile(profile):
 if type(profile)is not dict or set(profile)!={'table','row','music','party','play_intro','force_no_flee','return_on_loss','allow_reserve','level_offset'}:
  raise ValueError('Complete explicit encounter action profile required')
 asset_parts(profile['table']);asset_parts(profile['music']);identifier(profile['row'])
 flags=('play_intro','force_no_flee','return_on_loss','allow_reserve')
 if any(type(profile[k])is not bool for k in flags):raise ValueError('Encounter action flags must be booleans')
 if type(profile['level_offset'])is not int or not -99<=profile['level_offset']<=999:raise ValueError('Encounter level offset bounds')
 party=profile['party']
 if type(party)not in (list,tuple) or len(party)>PARTY_CAPACITY:raise ValueError('Encounter party override supports zero to six members')
 seen=set();members=[]
 for row in party:
  if type(row)is not dict or set(row)!={'character','formation'}:raise ValueError('Explicit party member and formation required')
  name=identifier(row['character'])
  if name in seen or type(row['formation'])is not int or not 0<=row['formation']<=2:raise ValueError('Duplicate party member or formation bounds')
  seen.add(name);members.append(dict(row))
 return dict(profile,party=tuple(members))

def encode(profile):
 profile=validate_profile(profile);data=bytearray(END-CONFIG)
 flags=sum(int(profile[key])<<i for i,key in enumerate(('play_intro','force_no_flee','return_on_loss','allow_reserve')))
 struct.pack_into('<IiI',data,0,flags,profile['level_offset'],len(profile['party']))
 def text(at,value,size):data[at-CONFIG:at-CONFIG+size]=value.encode('ascii').ljust(size,b'\0')
 package,asset=asset_parts(profile['table']);text(276,package,256);text(532,asset,96);text(628,profile['row'],96)
 package,asset=asset_parts(profile['music']);text(724,package,256);text(980,asset,96)
 for i,row in enumerate(profile['party']):
  text(1076+i*96,row['character'],96);struct.pack_into('<I',data,12+i*4,row['formation'])
 return bytes(data)

def decode(data):
 if type(data)is not bytes or len(data)!=END-CONFIG:raise ValueError('Encounter action configuration extent')
 flags,offset,count=struct.unpack_from('<IiI',data)
 if flags>15 or count>PARTY_CAPACITY:raise ValueError('Encounter flags or party count')
 def text(at,size):
  raw=data[at-CONFIG:at-CONFIG+size];value=raw.split(b'\0',1)[0]
  if len(value)==size or raw!=value.ljust(size,b'\0'):raise ValueError('Encounter configuration string padding')
  return value.decode('ascii')
 profile=dict(table=text(276,256)+'.'+text(532,96),row=text(628,96),music=text(724,256)+'.'+text(980,96),level_offset=offset,
  **{key:bool(flags&(1<<i)) for i,key in enumerate(('play_intro','force_no_flee','return_on_loss','allow_reserve'))})
 profile['party']=tuple(dict(character=text(1076+i*96,96),formation=struct.unpack_from('<I',data,12+i*4)[0]) for i in range(count))
 result=validate_profile(profile)
 if encode(result)!=data:raise ValueError('Unused encounter configuration fields must be zero')
 return result
