"""Explicit character graph identity, never a caller-provided learned loadout.

One to nine skill definitions are supported. The first is the sole starter;
learned and equipped values come only from the validated live graph or save.
"""
import re,struct
SIZE=4556
def text(value,width):
 if type(value)is not str or not value or not value.isascii() or len(value)>=width or '\0' in value:raise ValueError('Invalid character graph string')
 return value.encode().ljust(width,b'\0')
def identifier(value):
 if type(value)is not str or re.fullmatch(r'[A-Za-z0-9_]{1,95}',value)is None:raise ValueError('Invalid character or skill ID')
 return text(value,96)
def asset(value):
 if type(value)is not str or re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.[A-Za-z0-9_]+',value)is None:raise ValueError('Canonical game asset required')
 package,leaf=value.rsplit('.',1)
 if package.rsplit('/',1)[1]!=leaf:raise ValueError('Asset leaf must match package')
 return text(package,256)+text(leaf,96)
def encode(profile):
 if type(profile)is not dict or set(profile)!={'character','graph','skills'}:raise ValueError('Explicit character restoration profile required')
 skills=profile['skills']
 if type(skills)not in (tuple,list) or not 1<=len(skills)<=9:raise ValueError('One to nine graph skills required')
 data=bytearray(identifier(profile['character'])+asset(profile['graph'])+struct.pack('<I',len(skills)))
 seen=set();assets=set()
 for i,row in enumerate(skills):
  if type(row)is not dict or set(row)!={'id','asset','unlock_cost'}:raise ValueError('Explicit skill definition required')
  if row['id'] in seen or row['asset'] in assets:raise ValueError('Duplicate graph skill')
  seen.add(row['id']);assets.add(row['asset']);cost=row['unlock_cost']
  if type(cost)is not int or not 0<=cost<=99999:raise ValueError('Invalid unlock cost')
  data+=identifier(row['id'])+asset(row['asset'])+struct.pack('<II',cost,int(i==0))
 return bytes(data).ljust(SIZE,b'\0')
def decode(data):
 if type(data)is not bytes or len(data)!=SIZE:raise ValueError('Character graph profile size')
 def string(at,n):
  raw=data[at:at+n];end=raw.find(b'\0')
  if end<1 or any(raw[end:]):raise ValueError('Character graph string padding')
  return raw[:end].decode('ascii')
 n=struct.unpack_from('<I',data,448)[0]
 if not 1<=n<=9:raise ValueError('Graph skill count')
 profile=dict(character=string(0,96),graph=string(96,256)+'.'+string(352,96),skills=[])
 for i in range(n):
  at=452+i*456
  profile['skills'].append(dict(id=string(at,96),asset=string(at+96,256)+'.'+string(at+352,96),unlock_cost=struct.unpack_from('<I',data,at+448)[0]))
 if encode(profile)!=data:raise ValueError('Graph flags or unused profile bytes')
 return profile
