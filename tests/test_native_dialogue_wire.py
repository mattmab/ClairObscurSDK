import struct
import unittest
from types import SimpleNamespace as N
from expedition33._native_dialogue_wire import encode,validate_request,SIZE

class NativeDialogueWireTests(unittest.TestCase):
    def packet(self,**kw):
        return encode(7,9,N(index=1,serial=2,address=0x10000),N(index=3,serial=4,address=0x20000),N(index=5,serial=6,address=0x30000),kw.pop('texts',('First response','Second response')),**kw)
    def test_choices_and_unicode_lines_have_copied_contiguous_text_only(self):
        data=self.packet();validate_request(data);self.assertEqual(len(data),SIZE)
        line=self.packet(texts=('You found me. ✨',),speaker=N(index=7,serial=8,address=0x40000));validate_request(line)
        self.assertEqual(struct.unpack_from('<I',line,96)[0],0)
    def test_rejects_unbounded_malformed_or_inconsistent_text(self):
        for texts in ((),['a']*17,['a'*4096],['a'*3000]*3,['bad\0text'],['\ud800']):
            with self.assertRaises(ValueError):self.packet(texts=texts)
        for offset,value in ((0,4),(12,1),(96,2),(100,0),(104,8193),(108,1),(112,1),(176,4097)):
            data=bytearray(self.packet());struct.pack_into('<I',data,offset,value)
            with self.assertRaises(ValueError):validate_request(bytes(data))
    def test_rejects_smuggled_speaker_pointer_padding_and_unused_slots(self):
        for at in (72,120,184,16624,SIZE-1):
            data=bytearray(self.packet());data[at]=1
            with self.assertRaises(ValueError):validate_request(bytes(data))

    def test_native_end_has_no_borrowed_text_or_speaker(self):
        packet=self.packet(texts=(),finish=True);validate_request(packet)
        self.assertEqual(struct.unpack_from('<III',packet,96),(2,0,0))
        self.assertFalse(any(packet[112:]))
        with self.assertRaises(ValueError):self.packet(texts=('not an end payload',),finish=True)
        with self.assertRaises(ValueError):self.packet(texts=(),finish=True,speaker=N(index=1,serial=2,address=0x40000))
        changed=bytearray(packet);struct.pack_into('<I',changed,100,1)
        with self.assertRaises(ValueError):validate_request(bytes(changed))
