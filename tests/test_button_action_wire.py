import struct
import unittest
from expedition33 import _button_action_wire as wire


def reply(sent, *, state=2, registration=12, error=0, outcome=2, events=(), dropped=0):
    result=bytearray(sent)
    struct.pack_into('<4I',result,8,error,outcome,len(events),state)
    struct.pack_into('<2Q',result,56,dropped,registration)
    for i,event in enumerate(events): wire.EVENT.pack_into(result,72+i*40,*event)
    return result


class ButtonActionWireTests(unittest.TestCase):
    def test_request_contract(self):
        packet=wire.request('bind',2,3,action=4)
        self.assertEqual(len(packet),2632)
        self.assertEqual(wire.HEADER.unpack_from(packet),(1,1,0,0,0,0,0,0,2,3,4,0,0))
        for value in (0,-1,True,2**64):
            with self.assertRaises(ValueError): wire.request('bind',value,3,action=4)
            with self.assertRaises(ValueError): wire.request('bind',2,value,action=4)
            with self.assertRaises(ValueError): wire.request('bind',2,3,action=value)
        for operation in ('drain','unbind','status'):
            with self.assertRaises(ValueError): wire.request(operation,2,3,action=4)

    def test_success_and_lifecycle(self):
        for operation,state,registration in [('bind',2,12),('status',2,12),('unbind',0,0)]:
            sent=wire.request(operation,2,3,action=4 if operation=='bind' else 0)
            result=wire.decode(sent,reply(sent,state=state,registration=registration).hex(),session=7)
            self.assertEqual(result.state,state)
        sent=wire.request('drain',2,3)
        result=wire.decode(sent,reply(sent,events=[(7,12,2,4,8),(7,12,2,4,9)],dropped=2).hex(),session=7)
        self.assertEqual([event.sequence for event in result.events],[8,9])
        self.assertEqual(result.dropped,2)

    def test_reject_foreign_and_unordered(self):
        sent=wire.request('drain',2,3)
        for bad in [(8,12,2,4,8),(7,13,2,4,8),(7,12,3,4,8),(7,12,2,0,8),(7,12,2,4,0)]:
            with self.assertRaises(ValueError): wire.decode(sent,reply(sent,events=[bad]).hex(),session=7)
        with self.assertRaises(ValueError):
            wire.decode(sent,reply(sent,events=[(7,12,2,4,8)]*2).hex(),session=7)

    def test_correlation_and_output_bounds(self):
        sent=wire.request('drain',2,3)
        for offset in (0,4,24,28,32,40,48,72):
            changed=reply(sent); changed[offset]^=1
            with self.assertRaises(ValueError): wire.decode(sent,changed.hex(),session=7)
        changed=reply(sent); struct.pack_into('<I',changed,16,65)
        with self.assertRaises(ValueError): wire.decode(sent,changed.hex(),session=7)
        for state,registration in ((1,0),(4,0),(6,0),(2,0),(0,12),(0,0)):
            with self.assertRaises(ValueError): wire.decode(sent,reply(sent,state=state,registration=registration).hex(),session=7)
        with self.assertRaises(ValueError): wire.decode(sent,b'',session=7)
        with self.assertRaises(ValueError): wire.decode(sent,reply(sent).hex(),session=True)

    def test_unknown_never_delivers_partial_events(self):
        sent=wire.request('drain',2,3)
        result=wire.decode(sent,reply(sent,error=916,outcome=1,events=[(7,12,2,4,8)]).hex(),session=7)
        self.assertEqual((result.outcome,result.events,result.registration),('unknown',(),0))
        for error,outcome in ((910,0),(911,2),(912,2),(913,2),(914,2)):
            result=wire.decode(sent,reply(sent,error=error,outcome=outcome,state=0,registration=0).hex(),session=7)
            self.assertEqual(result.error,error)
        with self.assertRaises(ValueError): wire.decode(sent,reply(sent,error=914,events=[(7,12,2,4,8)]).hex(),session=7)
        with self.assertRaises(ValueError): wire.decode(sent,reply(sent,error=915).hex(),session=7)


if __name__=='__main__': unittest.main()
