"""Character-specific menu assets and transforms, with no built-in character."""
import math,re,struct
from ._story_wardrobe_profile import INPUTS,DYNAMIC
PATHS=tuple(DYNAMIC.values())
NAMES=('character','template_character','template_component','anchor_component','anchor_tag','default_skin','default_face')
SIZE=2616
def encode(profile):
 if type(profile)is not dict or set(profile)!={*PATHS,*NAMES,'party_offset'}:raise ValueError('Complete wardrobe profile required')
 out=bytearray()
 for key in PATHS:
  value=profile[key]
  if type(value)is not str or not value.isascii() or len(value)>=384 or re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+\.[A-Za-z0-9_]+',value)is None:raise ValueError('Invalid wardrobe asset')
  package,leaf=value.rsplit('.',1);base=package.rsplit('/',1)[1]
  if leaf!=base+('_C' if key in ('preview_class','body_anim','face_anim') else ''):raise ValueError('Wardrobe object/class suffix mismatch')
  out+=value.encode().ljust(384,b'\0')
 for key in NAMES:
  value=profile[key]
  if type(value)is not str or re.fullmatch(r'[A-Za-z0-9_]{1,95}',value)is None:raise ValueError('Invalid wardrobe identity')
  out+=value.encode().ljust(96,b'\0')
 offset=profile['party_offset']
 if type(offset)not in (tuple,list) or len(offset)!=3 or any(type(v)not in (int,float) or not math.isfinite(v) or abs(v)>1000 for v in offset):raise ValueError('Invalid wardrobe placement')
 out+=struct.pack('<3d',*offset)
 return bytes(out)
def decode(data):
 if type(data)is not bytes or len(data)!=SIZE:raise ValueError('Wardrobe profile size')
 out={};at=0
 for names,width in ((PATHS,384),(NAMES,96)):
  for key in names:
   value=data[at:at+width];at+=width;end=value.find(b'\0')
   if end<1 or any(value[end:]):raise ValueError('Wardrobe string padding')
   out[key]=value[:end].decode('ascii')
 out['party_offset']=struct.unpack_from('<3d',data,at)
 if encode(out)!=data:raise ValueError('Wardrobe profile encoding')
 return out
def inputs(profile):
 profile=decode(encode(profile))
 return tuple(dict(row,path=profile[DYNAMIC[i]]) if i in DYNAMIC else dict(row) for i,row in enumerate(INPUTS))
