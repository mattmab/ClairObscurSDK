import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import _sequence_seek as wire,_sequence_owner as owner_wire
from expedition33.sequences import OwnedLevelSequence

FUNCTION=N(index=12,serial=3,address=0x10000)


class SequenceSeekTests(unittest.TestCase):
    def test_interactive_preparation_refreshes_metadata_without_preparing_an_endpoint(self):
        sequence=object.__new__(OwnedLevelSequence)
        sequence.scope=N(_check=Mock(),_session=N(_transport=N(frame_time_values_protocol=1,sequence_seek_protocol=1)))
        sequence.state='ready';sequence.uncertain=False;sequence._endpoint=None;sequence._completion_invalidated=False
        sequence.catalog=object();sequence._prepare_seek_function=Mock()
        sequence._refresh_playback_metadata=Mock();sequence._call=Mock(side_effect=AssertionError('No redundant playback queries'))
        with patch('expedition33._sequence_endpoint.current_owned_context',side_effect=AssertionError('No unused endpoint context')):
            sequence.prepare_scrubbing()
        sequence._refresh_playback_metadata.assert_called_once_with(include_seek=True)
        sequence._prepare_seek_function.assert_called_once_with(sequence.catalog)
        self.assertTrue(sequence._completion_invalidated);self.assertIsNone(sequence._endpoint)
        with self.assertRaises(RuntimeError):sequence.prepare_completion()
        with self.assertRaises(RuntimeError):sequence.prepare_scrubbing()

    def test_scrubbing_preparation_rejects_unavailable_protocol_before_refresh(self):
        for cap in (0,True,None):
            sequence=object.__new__(OwnedLevelSequence)
            sequence.scope=N(_check=Mock(),_session=N(_transport=N(frame_time_values_protocol=1,sequence_seek_protocol=cap)))
            sequence.state='ready';sequence.uncertain=False;sequence._endpoint=None;sequence._completion_invalidated=False
            sequence._refresh_playback_metadata=Mock()
            with self.assertRaises(RuntimeError):sequence.prepare_scrubbing()
            sequence._refresh_playback_metadata.assert_not_called()

    def test_first_seek_stabilizes_function_once_before_reusing_its_identity(self):
        sequence=object.__new__(OwnedLevelSequence)
        sequence.scope=N(pid=123,_check=lambda:None,_session=N(_transport=N(sequence_seek_protocol=1)))
        sequence.state='ready';sequence.uncertain=False;sequence._endpoint=None
        sequence._completion_invalidated=False;sequence._seek_function=None
        cls=N(index=5,name='MovieSceneSequencePlayer',class_name='Class',outer_index=0)
        observed=N(index=12,serial=0,address=0x10000,name='SetPlaybackPosition',class_name='Function',outer_index=5)
        stable=N(index=12,serial=1001,address=0x10000)
        sequence.owner=N(state='armed',seek_frame=Mock())
        with patch('expedition33.sequences.capture_matching',return_value=N(objects=[cls,observed])) as capture,patch('expedition33._stable_lease.acquire_stable',return_value=(N(object=stable),object())) as acquire:
            sequence.seek_frame(12);sequence.seek_frame(18)
        capture.assert_called_once();acquire.assert_called_once_with(sequence.scope,observed)
        self.assertEqual(sequence.owner.seek_frame.call_args_list[0].args,(stable,12,0.))
        self.assertEqual(sequence.owner.seek_frame.call_args_list[1].args,(stable,18,0.))

    def test_prepared_scrubber_reuses_fresh_metadata_and_scope_owned_function(self):
        sequence=object.__new__(OwnedLevelSequence)
        sequence.scope=N(pid=123,_check=Mock(),_session=N(_transport=N(frame_time_values_protocol=1,sequence_seek_protocol=1)))
        sequence.state='ready';sequence.uncertain=False;sequence._endpoint=None
        sequence._completion_invalidated=False;sequence._seek_function=None
        cls=N(index=5,name='MovieSceneSequencePlayer',class_name='Class',outer_index=0)
        observed=N(index=12,serial=0,address=0x10000,name='SetPlaybackPosition',class_name='Function',outer_index=5)
        stable=N(index=12,serial=1001,address=0x10000)
        fresh=N(objects=[cls,observed]);sequence._refresh_playback_metadata=Mock(side_effect=lambda **_:setattr(sequence,'catalog',fresh))
        sequence.owner=N(state='armed',seek_frame=Mock())
        with patch('expedition33.sequences.capture_matching',side_effect=AssertionError('second scan')) as capture,\
             patch('expedition33._stable_lease.acquire_stable',return_value=(N(object=stable),object())) as acquire:
            sequence.prepare_scrubbing();sequence.seek_frame(12)
        capture.assert_not_called();acquire.assert_called_once_with(sequence.scope,observed)
        sequence.owner.seek_frame.assert_called_once_with(stable,12,0.)

    def test_stale_prepared_seek_descriptor_fails_without_fallback_or_dispatch(self):
        from expedition33 import RuntimeQueryError
        sequence=object.__new__(OwnedLevelSequence)
        sequence.scope=N(pid=123,_check=Mock(),_session=N(_transport=N(frame_time_values_protocol=1,sequence_seek_protocol=1)))
        sequence.state='ready';sequence.uncertain=False;sequence._endpoint=None
        sequence._completion_invalidated=False;sequence._seek_function=None
        cls=N(index=5,name='MovieSceneSequencePlayer',class_name='Class',outer_index=0)
        stale=N(index=12,serial=2,address=0x10000,name='SetPlaybackPosition',class_name='Function',outer_index=5)
        sequence._refresh_playback_metadata=Mock(side_effect=lambda **_:setattr(sequence,'catalog',N(objects=[cls,stale])))
        sequence.owner=N(state='armed',seek_frame=Mock())
        with patch('expedition33.sequences.capture_matching',side_effect=AssertionError('fallback scan')) as capture,\
             patch('expedition33._stable_lease.acquire_stable',side_effect=RuntimeQueryError('identity changed')) as acquire:
            with self.assertRaisesRegex(RuntimeQueryError,'identity changed'):sequence.prepare_scrubbing()
        capture.assert_not_called();acquire.assert_called_once_with(sequence.scope,stale)
        sequence.owner.seek_frame.assert_not_called();self.assertIsNone(sequence._seek_function)

    def test_fixed_packet_roundtrip_and_malformed_replies(self):
        request=wire.encode(FUNCTION,-1,.5);self.assertEqual(len(request),64)
        self.assertEqual(wire.decode(request,request[:32]+struct.pack('<I',1)+request[36:]),1)
        for offset in (0,8,24,36,63):
            bad=bytearray(request);bad[offset]^=1
            with self.assertRaises(ValueError):wire.decode(request,bytes(bad))
        with self.assertRaises(ValueError):wire.decode(request,request[:32]+struct.pack('<I',3)+request[36:])
        for frame,sub in ((True,0),(1<<31,0),(0,float('nan')),(0,float('inf')),(0,-.1),(0,1),(0,True),(0,.999999999999)):
            with self.subTest(frame=frame,sub=sub):
                with self.assertRaises(ValueError):wire.encode(FUNCTION,frame,sub)

    def make_owner(self,error=0,state=1,outcome=1):
        def command(name,data):
            owner_wire.validate_request(data)
            response=data[:24]+struct.pack('<II',error,state)+data[32:64]+struct.pack('<I',outcome)+data[68:]
            return dict(sequence_owner_packet=response.hex())
        transport=N(sequence_seek_protocol=1,command=Mock(side_effect=command))
        session=N(_check=lambda:None,_transport=transport,_abort_ownership=Mock())
        owner=owner_wire.NativeSequenceOwner(N(_session=session));owner.state='armed'
        return owner,session

    def test_returned_seek_and_known_rejection_preserve_owner(self):
        owner,session=self.make_owner();self.assertTrue(owner.seek_frame(FUNCTION,4,.25))
        self.assertEqual(owner.state,'armed');session._abort_ownership.assert_not_called()
        for error in (1691,1595,407):
            owner,session=self.make_owner(error=error,outcome=0)
            with self.assertRaisesRegex(RuntimeError,'before dispatch'):owner.seek_frame(FUNCTION,4)
            self.assertEqual(owner.state,'armed');session._abort_ownership.assert_not_called()

    def test_unknown_or_inconsistent_acknowledgement_aborts_without_retry(self):
        for error,state,outcome in ((1693,2,2),(0,1,0),(1691,1,1),(0,3,1)):
            owner,session=self.make_owner(error,state,outcome)
            with self.assertRaises(RuntimeError):owner.seek_frame(FUNCTION,4)
            session._abort_ownership.assert_called_once();session._transport.command.assert_called_once()
            self.assertEqual(owner.state,'unknown')

    def test_feature_gate_and_hidden_tail_rejected_before_dispatch(self):
        owner,session=self.make_owner();session._transport.sequence_seek_protocol=0
        with self.assertRaises(RuntimeError):owner.seek_frame(FUNCTION,4)
        session._transport.command.assert_not_called()
        data=owner_wire.HEADER.pack(1,8,12,0,0,0)+wire.encode(FUNCTION,4)+bytes(owner_wire.SIZE-96)
        owner_wire.validate_request(data)
        with self.assertRaises(ValueError):owner_wire.validate_request(data[:-1]+b'\1')

    def test_scrubbing_cancels_completion_and_known_rejection_does_not_poison_cleanup(self):
        sequence=object.__new__(OwnedLevelSequence)
        sequence.scope=N(_check=lambda:None,_session=N(_transport=N(sequence_seek_protocol=1)))
        sequence.state='playing';sequence.uncertain=False;sequence._endpoint=N(state='playing')
        endpoint=sequence._endpoint;sequence._completion_invalidated=False;sequence._seek_function=FUNCTION
        sequence.owner=N(state='armed',seek_frame=Mock());sequence.pause=Mock(side_effect=lambda:setattr(sequence,'state','paused'))
        self.assertTrue(sequence.seek_frame(4,.5));sequence.pause.assert_called_once()
        self.assertEqual(endpoint.state,'cancelled');self.assertIsNone(sequence._endpoint)
        self.assertTrue(sequence._completion_invalidated);self.assertFalse(sequence.uncertain)
        sequence.owner.seek_frame.side_effect=RuntimeError('known rejection')
        with self.assertRaises(RuntimeError):sequence.seek_frame(5)
        self.assertFalse(sequence.uncertain)
        def unknown(*args):sequence.owner.state='unknown';raise RuntimeError('lost')
        sequence.owner.seek_frame.side_effect=unknown
        with self.assertRaises(RuntimeError):sequence.seek_frame(6)
        self.assertTrue(sequence.uncertain)
