"""Explicit sequence impacts and input bonus for one owned attack adapter."""
import math,re,struct
SIZE=1320
PATHS=('sequence','character_class','script_class')
def encode(profile):
 if type(profile)is not dict or set(profile)!={*PATHS,'impacts','validity','anticipation','lead','bonus_per_input','damage_reason'}:raise ValueError('Complete battle QTE profile required')
 out=bytearray()
 for i,key in enumerate(PATHS):
  value=profile[key]
  if type(value)is not str or len(value)>=384 or re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.[A-Za-z0-9_]+',value)is None:raise ValueError('Canonical QTE asset required')
  package,leaf=value.rsplit('.',1)
  if leaf!=package.rsplit('/',1)[1]+('_C' if i else ''):raise ValueError('QTE class suffix mismatch')
  out+=value.encode('ascii').ljust(384,b'\0')
 impacts=profile['impacts']
 if type(impacts)not in (list,tuple) or not 1<=len(impacts)<=16 or any(type(x)not in (float,int) or not math.isfinite(x) or not 0<x<=3600 for x in impacts) or any(a>=b for a,b in zip(impacts,impacts[1:])):raise ValueError('One to sixteen ordered impacts required')
 out+=struct.pack('<I16d',len(impacts),*impacts,*([0.]*(16-len(impacts))))
 values=tuple(profile[k] for k in ('validity','anticipation','lead','bonus_per_input'))
 if any(type(x)not in (float,int) or not math.isfinite(x) for x in values):raise ValueError('Finite QTE intervals required')
 validity,anticipation,lead,bonus=values
 if not 0<validity<=10 or not 0<=anticipation<=10 or not 0<lead<=1 or not 0<=bonus<=10:raise ValueError('QTE timing or bonus outside bounds')
 reason=profile['damage_reason']
 if type(reason)is not int or not 0<=reason<=255:raise ValueError('Invalid damage reason')
 return bytes(out)+struct.pack('<4dI',*values,reason)
def decode(data):
 if type(data)is not bytes or len(data)!=SIZE:raise ValueError('Battle QTE profile size')
 p={}
 for i,key in enumerate(PATHS):
  value=data[i*384:(i+1)*384];end=value.find(b'\0')
  if end<1 or any(value[end:]):raise ValueError('QTE string padding')
  p[key]=value[:end].decode('ascii')
 count,*impacts=struct.unpack_from('<I16d',data,1152)
 if not 1<=count<=16:raise ValueError('QTE impact count')
 p['impacts']=tuple(impacts[:count]);p.update(zip(('validity','anticipation','lead','bonus_per_input','damage_reason'),struct.unpack_from('<4dI',data,1284)))
 if encode(p)!=data:raise ValueError('QTE unused slots or padding')
 return p
