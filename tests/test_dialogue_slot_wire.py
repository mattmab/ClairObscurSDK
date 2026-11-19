import struct,unittest
from types import SimpleNamespace as N
from expedition33._dialogue_slot_wire import validate
class SlotWireTests(unittest.TestCase):
    def plan(self):
        data=bytearray(48);struct.pack_into('<3fi2f',data,16,.35,.35,1.,10000,-1.,0.)
        return N(entry_rva=0x33a3bc0,function_flags=67240963,function=N(name='PlaySlotAnimationAsDynamicMontage'),parameter_size=48,allocation_extent=48,return_offset=40,texts=(('SlotNodeName','Mouth'),),data=bytes(data))
    def test_only_qualified_slots_and_profile_pass(self):
        p=self.plan();validate(p)
        for field,value in [('entry_rva',1),('function_flags',0),('texts',(('SlotNodeName','OtherSlot'),)),('parameter_size',49)]:
            p=self.plan();setattr(p,field,value)
            with self.assertRaises(ValueError):validate(p)
    def test_unreviewed_loop_count_rejected(self):
        p=self.plan();d=bytearray(p.data);struct.pack_into('<i',d,28,20000);p.data=bytes(d)
        with self.assertRaises(ValueError):validate(p)
