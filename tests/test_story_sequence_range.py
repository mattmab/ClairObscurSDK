import struct,unittest
from contextlib import nullcontext
from unittest.mock import Mock,patch
from types import SimpleNamespace as NS
from expedition33 import story_sequence_range as wire
def held(index):return NS(object=NS(index=index,serial=2,address=0x10000+index*16),_token=index+10)
class GommageRangeWire(unittest.TestCase):
    def sent(self,mode=0):return wire.packet(5,held(1),held(2),'e33c5701000000010000000200000003',mode)
    def test_only_verified_range_and_save_namespace(self):
        sent=self.sent();wire.validate(sent)
        for offset in (72,92,96,104):
            changed=bytearray(sent);changed[offset]^=1
            with self.assertRaises(ValueError):wire.validate(bytes(changed))
    def test_range_apply_inspect_restore_readback(self):
        for mode in range(3):
            sent=self.sent(mode);reply=bytearray(sent);struct.pack_into('<I',reply,12,mode+1)
            value=6493600 if mode==2 else 7261600;struct.pack_into('<I',reply,100,value)
            self.assertEqual(wire.decode(sent,bytes(reply)),value)
            reply[40]^=1
            with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))

class RangePreparationContext(unittest.TestCase):
    def owner(self):
        owner=object.__new__(wire.StorySequenceRange)
        owner.started=False;owner.held=[];owner.scope=NS(pid=123)
        owner.sequence='gommage';owner.scene=None
        owner.resources=NS(load=Mock(return_value=NS(index=10,serial=2,address=1234)))
        owner.hold=Mock(side_effect=lambda value:NS(object=value))
        owner.send=Mock();owner.context=Mock(side_effect=AssertionError('Dialogue discovery is unrelated'))
        return owner

    def test_fresh_game_instance_without_dialogue_discovery(self):
        owner=self.owner();gi=object();scene=object();catalog=object()
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()), \
             patch('expedition33.story_save_identity.observe',return_value=(None,None,None,None,gi,None)) as observe, \
             patch('expedition33.catalog.capture_selected',return_value=catalog), \
             patch('expedition33.catalog.capture_matching',side_effect=AssertionError('No registry scan')), \
             patch('expedition33.values.read_values_with_references',return_value=(NS(errors={},values={(10,'MovieScene'):scene}),catalog)):
            self.assertIs(owner.prepare(),owner)
        observe.assert_called_once_with(owner.scope)
        self.assertIs(owner.gi.object,gi);self.assertIs(owner.scene.object,scene)
        owner.send.assert_called_once_with(0);self.assertTrue(owner.started)

    def test_context_rejection_never_loads_or_dispatches(self):
        owner=self.owner()
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()), \
             patch('expedition33.story_save_identity.observe',side_effect=RuntimeError('Changed world')):
            with self.assertRaisesRegex(RuntimeError,'Changed world'):owner.prepare()
        owner.resources.load.assert_not_called();owner.send.assert_not_called()
        self.assertFalse(owner.started)
