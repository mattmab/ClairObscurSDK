import math,struct,unittest
from types import SimpleNamespace
from expedition33 import _story_inworld_wire as wire
from expedition33.story_inworld import InWorldDialogue

def packet(**changes):
    obj=SimpleNamespace(index=5,serial=6,address=0x10000)
    objects=dict.fromkeys(wire.NAMES,obj)
    line=dict(text='Exact walking dialogue é',character=9,delay_to_delete=4.4,delay_to_answer=.5)
    line.update(changes)
    return wire.encode(1,2,3,4,objects,lines=(line,))

class InWorldWire(unittest.TestCase):
    def test_transport_routes_new_operation_and_requires_exact_capability(self):
        from test_menu_transport import MenuTransportTests
        p=packet()
        for capability in (0,True,2,1):
            transport=MenuTransportTests().transport();transport.mesh_protocol=3
            transport.story_inworld_dialogue_protocol=capability
            transport._read=lambda:dict(event='session_response',command='mesh',closed=False)
            if type(capability) is int and capability==1:
                transport.command('mesh',p)
                self.assertEqual(transport._process.stdin.getvalue(),'mesh '+p.hex()+'\n')
            else:
                with self.assertRaises(ValueError):transport.command('mesh',p)
                self.assertEqual(transport._process.stdin.getvalue(),'')
    def test_exact_copied_layout_and_unicode(self):
        p=packet();wire.validate(p)
        self.assertEqual(struct.unpack_from('<4I',p,176),(0,1,25,0))
        self.assertEqual(struct.unpack_from('<I',p,wire.LINES)[0],9)
        self.assertEqual(struct.unpack_from('<2d',p,wire.LINES+24),(4.4,.5))
        self.assertEqual(p[wire.TEXT:wire.TEXT+50].decode('utf-16-le'),'Exact walking dialogue é\0')
    def test_rejects_unqualified_portraits_and_nonfinite_timing(self):
        for fields in ({'character':8},{'emotion':1},{'delay_to_delete':math.nan},{'delay_to_answer':-1},{'text':'bad\0text'}):
            with self.assertRaises(ValueError):packet(**fields)
    def test_receipt_cannot_cross_playbacks(self):
        p=packet();reply=bytearray(p);struct.pack_into('<I',reply,12,2)
        self.assertEqual(wire.decode(p,bytes(reply)),'completed')
        struct.pack_into('<Q',reply,24,999)
        with self.assertRaises(RuntimeError):wire.decode(p,bytes(reply))
    def test_close_retry_does_not_repeat_native_detach(self):
        playback=InWorldDialogue.__new__(InWorldDialogue)
        playback.closed=False;playback.unknown=False;playback.attempted=True;playback.detached=False;playback.state='completed'
        sent=[];retire=[False,True]
        playback._send=lambda mode:sent.append(mode) or 'completed'
        playback.carrier=SimpleNamespace(close=lambda:retire.pop(0))
        self.assertFalse(playback.close());self.assertTrue(playback.close())
        self.assertEqual(sent,[2])

if __name__=='__main__':unittest.main()
