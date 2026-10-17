import struct,unittest,sys,types,importlib,math
from pathlib import Path
from types import SimpleNamespace
from expedition33.procedural_mesh import SIZE,HEADER,validate_request
pkg=types.ModuleType('transform_test_builder');pkg.__path__=[str(Path(__file__).resolve().parents[1]/'mods/E33WorldBuilder')];sys.modules[pkg.__name__]=pkg
bulk=importlib.import_module(pkg.__name__+'.bulk');templates=importlib.import_module(pkg.__name__+'.templates')
POSE=[0,0,0,1,0,0,0,0,1,1,1,0]
class TransformBatchTests(unittest.TestCase):
 def packet(self):
  p=bytearray(SIZE);HEADER.pack_into(p,0,3,66,0,0,17);struct.pack_into('<I',p,2000,128)
  for i in range(128):struct.pack_into('<iiQ12d',p,4096+112*i,i,2,0x10000+16*i,*POSE)
  return p
 def test_full_packet_and_invalid_rows(self):
  validate_request(bytes(self.packet()))
  for fmt,at,v in [('<I',2000,129),('<B',2004,1),('<Q',4104,0),('<d',4112,float('nan')),('<B',4096+112*128,1)]:
   p=self.packet();struct.pack_into(fmt,p,at,v)
   with self.subTest(at=at),self.assertRaises(ValueError):validate_request(bytes(p))
 def test_drag_flag(self):
  p=bytearray(SIZE);HEADER.pack_into(p,0,3,67,0,0,17);struct.pack_into('<d',p,2000,1);validate_request(bytes(p))
  struct.pack_into('<d',p,2000,2)
  with self.assertRaises(ValueError):validate_request(bytes(p))
 def test_partial_acknowledgement_preserves_queue(self):
  calls=[];raw=bytearray(SIZE);struct.pack_into('<I',raw,3560,47)
  mod=SimpleNamespace(last_raw=raw,command=lambda op,bulk:calls.append((op,bulk)))
  lib=SimpleNamespace(mod=mod,owned={str(i):{'component':(i,2,0x10000+i*16)} for i in range(200)})
  moves=[(str(i),POSE) for i in range(200)];done=bulk.transform_batch(lib,moves);del moves[:done]
  self.assertEqual(done,47);self.assertEqual(len(calls[0][1]),128);self.assertEqual(moves[0][0],'47')
 def test_framing_centers_group_in_camera_direction(self):
  rows=[{'transform':[0,0,0,1,100,200,300,0,1,1,1,0]},{'transform':[0,0,0,1,1100,2200,3300,0,1,1,1,0]}]
  origin=templates.framed_origin(rows,[10,20,30],[30,90,0]);center=[origin[i]+[600,1200,1800][i] for i in range(3)];direction=[center[i]-[10,20,30][i] for i in range(3)]
  self.assertAlmostEqual(direction[0],0,places=6);self.assertGreater(direction[1],0);self.assertAlmostEqual(direction[2]/direction[1],math.tan(math.radians(30)))
 def test_large_preview_stays_within_fifty_metres(self):
  rows=[{'transform':POSE[:4]+[x,0,0,0,1,1,1,0]} for x in (-30000,30000)]
  origin=templates.framed_origin(rows,[10,20,30],[-40,90,0])
  self.assertAlmostEqual(math.dist(origin,[10,20,30]),5000.)
 def test_bring_here_preserves_rotation_and_pending_rows(self):
  rows=[{'transform':POSE[:4]+[x,0,0,0,1,1,1,0]} for x in (100,900)]
  mod=SimpleNamespace(command=lambda op:None,last={'position':[10,20,30],'rotation':[0,0,0]})
  lib=SimpleNamespace(mod=mod,message='');t=templates.Templates.__new__(templates.Templates)
  t.mod=mod;t.library=lib;t.draft=[('a',rows[0])];t.queue=[rows[1]];t.yaw=90
  t.bring_here()
  rotated=[{'transform':templates.placed(row['transform'],[0,0,0],[0,0,0],90)} for row in rows]
  self.assertEqual(t.origin,templates.framed_origin(rotated,[10,20,30],[0,0,0]))
  self.assertEqual(t.delta,[0,0,0]);self.assertEqual(t.yaw,90);self.assertEqual(len(t.moves),1);self.assertEqual(t.queue,[rows[1]])
if __name__=='__main__':unittest.main()
