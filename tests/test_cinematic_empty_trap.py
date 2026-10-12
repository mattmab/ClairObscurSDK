import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import _cinematic_sound_event as m

class EmptyTrapTests(unittest.TestCase):
    def setUp(self):
        self.state=1;self.failed=0;self.observed=0
        self.transport=N(cinematic_empty_title_protocol=1,command=Mock(side_effect=self.reply))
        self.session=N(_transport=self.transport,_check=Mock(),_abort_ownership=Mock())
        self.scope=N(_session=self.session,_check=Mock(),pid=7,_audio_owners=[],retain=Mock(return_value=N(_token=17)))
        self.owner=m.NativeCinematicSoundEvent(self.scope)
        self.fn=N(pid=7,index=1,serial=2,address=100);self.player=N(pid=7,index=3,serial=4,address=200)
    def reply(self,command,data):
        out=bytearray(data);struct.pack_into('<IIII',out,24,0,self.state,self.observed,self.failed)
        return {'cinematic_sound_event_packet':out.hex()}
    def test_empty_packet_has_no_sound_or_dispatch_and_controlled_failure_cleans(self):
        self.owner.prepare_empty(self.fn,self.player);data=self.transport.command.call_args.args[1]
        self.assertEqual(m.HEADER.unpack_from(data)[:2],(2,1));self.assertFalse(any(data[72:88]));self.assertFalse(any(data[96:]))
        self.state=2;self.observed=self.failed=1
        self.assertEqual(self.owner.status()['state'],'quarantined');self.session._abort_ownership.assert_not_called()
        self.state=0;self.assertTrue(self.owner.close());self.assertEqual(self.owner.state,'closed');self.session._abort_ownership.assert_not_called()
    def test_v1_does_not_accept_quarantine_or_historical_failure(self):
        self.state=2;self.observed=self.failed=1
        with self.assertRaises(RuntimeError):self.owner.status()
        self.session._abort_ownership.assert_called_once()
    def test_v2_malformed_failed_counter_aborts(self):
        self.owner.prepare_empty(self.fn,self.player);self.state=2;self.failed=1;self.observed=0
        with self.assertRaises(ValueError):self.owner.status()
        self.session._abort_ownership.assert_called_once()
    def test_empty_packet_rejects_nonzero_sound_or_invocation(self):
        self.owner.prepare_empty(self.fn,self.player);data=self.transport.command.call_args.args[1]
        for offset in (72,96):
            altered=bytearray(data);altered[offset]=1
            with self.assertRaises(ValueError):m.validate_request(bytes(altered))
    def test_wrong_capability_rejected_before_retention(self):
        self.transport.cinematic_empty_title_protocol=True
        with self.assertRaises(RuntimeError):self.owner.prepare_empty(self.fn,self.player)
        self.scope.retain.assert_not_called()

if __name__=='__main__':unittest.main()
