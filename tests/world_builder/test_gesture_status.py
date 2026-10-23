import sys,types,struct,unittest
from pathlib import Path
from contextlib import nullcontext
from unittest.mock import Mock
package=types.ModuleType('gesture_test_builder')
package.__path__=[str(Path(__file__).resolve().parents[2]/'mods/E33WorldBuilder')]
sys.modules[package.__name__]=package
from gesture_test_builder.mod import Mod

class GestureStatusTests(unittest.TestCase):
    def make_mod(self,axis,value,corrupt=False):
        mod=Mod();mod.owner=123;mod.status=Mock(return_value={})
        def reply(name,packet):
            raw=bytearray(packet)
            struct.pack_into('<2d',raw,4080,axis,value)
            if corrupt:raw[3392]=1
            return {'mesh_packet':raw.hex()}
        mod.session=types.SimpleNamespace(_lease_context=nullcontext,_session=types.SimpleNamespace(_transport=types.SimpleNamespace(command=reply)))
        return mod
    def test_accepts_active_rotation_and_scaling_status(self):
        for axis,label,value in ((1,'Yaw',-32.5),(2,'Pitch',90.),(3,'Roll',180.),(4,'Scale',1.5)):
            mod=self.make_mod(axis,value);mod.command(26)
            self.assertEqual(mod.last['rotation_axis'],label)
            self.assertEqual(mod.last['rotation_angle'],value)
    def test_rejects_invalid_gesture_status(self):
        for axis,value in ((5,1.),(4,float('nan')),(4,float('inf'))):
            with self.assertRaisesRegex(RuntimeError,'gesture status'):self.make_mod(axis,value).command(26)
    def test_other_padding_stays_protected(self):
        with self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):self.make_mod(4,1.5,True).command(26)
