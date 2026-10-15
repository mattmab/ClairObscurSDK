"""Versioned metadata and PNG thumbnail cache; never persist engine identities."""
import hashlib,json,math,struct,zlib
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'settings/E33WorldBuilder/cache/neutral-v1'
GAME=Path(__file__).resolve().parents[3]
@lru_cache(maxsize=1)
def build_key():
 paths=[GAME/'Sandfall/Binaries/Win64/SandFall-Win64-Shipping.exe']
 paths+=sorted(p for p in (GAME/'Sandfall/Content/Paks').glob('*') if p.suffix in ('.utoc','.pak'))
 return hashlib.sha256(repr([(p.name,p.stat().st_size,p.stat().st_mtime_ns) for p in paths if p.exists()]).encode()).hexdigest()
def thumbnail_key(asset):return hashlib.sha256((build_key()+':neutral-v1b:'+asset).encode()).hexdigest()

def cached_png(key):
 # Validate the small header here. The engine decoder validates image data;
 # decoding every pixel in Python before decoding it again in Unreal is wasteful.
 path=ROOT/(key+'.png')
 try:
  with path.open('rb') as source:header=source.read(33)
  if len(header)!=33 or header[:8]!=b'\x89PNG\r\n\x1a\n' or header[12:16]!=b'IHDR':return False
  return struct.unpack('>II',header[16:24])==(320,240) and header[24]==8 and header[25] in (2,6)
 except OSError:return False
def read_catalog():
 try:
  data=json.loads((ROOT/'catalog.json').read_text(encoding='utf8'))
  if data['build']!=build_key() or data['version']!=1:return None
  paths=data['meshes']
  if not isinstance(paths,list) or not 1<=len(paths)<=250000 or any(not isinstance(p,str) or not p.startswith('/Game/') or len(p)>512 for p in paths):return None
  return paths
 except (OSError,ValueError,KeyError,TypeError):return None
def write_catalog(paths):
 ROOT.mkdir(parents=True,exist_ok=True);p=ROOT/'catalog.json';tmp=p.with_suffix('.tmp')
 tmp.write_text(json.dumps(dict(version=1,build=build_key(),meshes=sorted(set(paths)))),encoding='utf8');tmp.replace(p)
def read_png(path):
 data=Path(path).read_bytes()
 if len(data)>4*1024*1024 or data[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid thumbnail PNG')
 at=8;packed=bytearray();w=h=channels=0
 while at+12<=len(data):
  n=struct.unpack_from('>I',data,at)[0];kind=data[at+4:at+8];payload=data[at+8:at+8+n];at+=n+12
  if kind==b'IHDR':
   w,h,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',payload)
   if (w,h)!=(320,240) or depth!=8 or color not in (2,6) or compression or filtering or interlace:raise ValueError('Unsupported thumbnail PNG')
   channels=3 if color==2 else 4
  elif kind==b'IDAT':packed.extend(payload)
  elif kind==b'IEND':break
 if not channels:raise ValueError('Missing PNG header')
 stride=w*channels
 decoder=zlib.decompressobj();raw=decoder.decompress(packed,(stride+1)*h+1)
 if not decoder.eof or decoder.unconsumed_tail:raise ValueError("Oversized or truncated PNG")
 if len(raw)!=(stride+1)*h:raise ValueError('Invalid PNG scanlines')
 result=bytearray(w*h*3);previous=bytearray(stride)
 for y in range(h):
  start=y*(stride+1);kind=raw[start];row=bytearray(raw[start+1:start+1+stride])
  if kind>4:raise ValueError('Invalid PNG filter')
  for x in range(stride):
   a=row[x-channels] if x>=channels else 0;b=previous[x];c=previous[x-channels] if x>=channels else 0
   if kind==1:value=a
   elif kind==2:value=b
   elif kind==3:value=(a+b)//2
   elif kind==4:
    p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c);value=a if pa<=pb and pa<=pc else b if pb<=pc else c
   else:value=0
   row[x]=(row[x]+value)&255
  for x in range(w):result[(y*w+x)*3:(y*w+x)*3+3]=row[x*channels:x*channels+3]
  previous=row
 return result
def write_png(path,rgb):
 def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
 scan=b''.join(b'\0'+rgb[y*960:(y+1)*960] for y in range(240))
 payload=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,240,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(scan,3))+chunk(b'IEND',b'')
 p=Path(path);tmp=p.with_suffix('.tmp');tmp.write_bytes(payload);tmp.replace(p)
def compose_python(key):
 base=read_png(ROOT/(key+'.base.png'));normal=read_png(ROOT/(key+'.normal.png'));out=bytearray(len(base))
 # SceneCapture normals are encoded from [-1,1] to [0,1]. Fixed white
 # key/fill illumination leaves all color independent of the active level.
 light=(-.65,-.35,.68);length=math.sqrt(sum(v*v for v in light));lx,ly,lz=(v/length for v in light)
 # Lookup tables and scalar arithmetic avoid millions of temporary lists,
 # generators and power operations while retaining the same lighting formula.
 normals=tuple(v/127.5-1 for v in range(256))
 gamma=tuple(255*(v/255)**(1/2.2) for v in range(256))
 for i in range(0,len(base),3):
  r,g,b=base[i],base[i+1],base[i+2]
  nr,ng,nb=normal[i],normal[i+1],normal[i+2]
  if not (nr or ng or nb or r or g or b):out[i:i+3]=b'\x2a\x2e\x35';continue
  x,y,z=normals[nr],normals[ng],normals[nb]
  length=math.sqrt(x*x+y*y+z*z)
  shade=.75+.25*max(0,(x*lx+y*ly+z*lz)/max(.001,length))
  out[i]=max(0,min(255,round(gamma[r]*shade)))
  out[i+1]=max(0,min(255,round(gamma[g]*shade)))
  out[i+2]=max(0,min(255,round(gamma[b]*shade)))
 write_png(ROOT/(key+'.png'),out)
 for suffix in ('.base.png','.normal.png'):(ROOT/(key+suffix)).unlink(missing_ok=True)
 return ROOT/(key+'.png')

def compose_timed(key):
 import time
 started=time.perf_counter();compose(key)
 return time.perf_counter()-started

@lru_cache(maxsize=1)
def native_composer():
 import ctypes
 path=GAME/'SDK/build/thumbnail-worker-v2/thumbnail_worker.dll'
 if not path.exists():return None
 library=ctypes.CDLL(str(path));fn=library.compose_thumbnail
 fn.argtypes=[ctypes.c_wchar_p]*3;fn.restype=ctypes.c_long
 return fn

def compose(key):
 fn=native_composer()
 if fn is None:return compose_python(key)
 raw=(ROOT/(key+'.base.rgb')).exists() and (ROOT/(key+'.normal.rgb')).exists()
 base=ROOT/(key+('.base.rgb' if raw else '.base.png'));normal=ROOT/(key+('.normal.rgb' if raw else '.normal.png'));output=ROOT/(key+'.png');temp=ROOT/(key+'.native.tmp')
 try:
  result=fn(str(base),str(normal),str(temp))
  if result<0:raise RuntimeError(f'Native thumbnail codec failed: {result:#x}')
  temp.replace(output)
 finally:temp.unlink(missing_ok=True)
 base.unlink(missing_ok=True);normal.unlink(missing_ok=True)
 return output
