from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from expedition33.cinematics.adapters import TitleAdapter, MediaAdapter
from expedition33.cinematics.controller import BackendState
from expedition33.cinematics.retirement import title_retirement_available, media_retirement_available

class RetirementAdapterTests(unittest.TestCase):
 def test_title_retirement_defers_without_discarding_sequence_or_compensating(self):
  adapter=TitleAdapter(None,{},None,None);sequence=Mock();sequence.retire_world.return_value=False
  adapter.backend=NS(sequence=sequence,adapters=Mock(),panel=Mock(),presentation=Mock(),state='playing')
  self.assertFalse(adapter.close(NS(epoch_valid=False)))
  self.assertIs(adapter.backend.sequence,sequence);adapter.backend.adapters.retire_world.assert_not_called()
  sequence.close.assert_not_called()
 def test_title_retirement_orders_native_then_tracking_and_never_restores(self):
  events=[];sequence=Mock();sequence.retire_world.side_effect=lambda **kwargs:events.append('sequence') or True
  owned=Mock();owned.retire_world.side_effect=lambda:events.append('adapters') or True
  panel=Mock();panel.retire_world.side_effect=lambda:events.append('panel') or 'ack'
  presentation=Mock();adapter=TitleAdapter(None,{},None,None)
  adapter.backend=NS(sequence=sequence,adapters=owned,panel=panel,presentation=presentation,state='playing')
  with patch('expedition33.cinematics.retirement.retire_presentation',side_effect=lambda p:events.append('presentation')):
   self.assertTrue(adapter.close(NS(epoch_valid=False)))
  self.assertEqual(events,['sequence','adapters','panel','presentation'])
  sequence.close.assert_not_called();presentation.restore.assert_not_called()
  self.assertIsNone(adapter.backend.sequence);self.assertEqual(adapter.backend.state,'retired')
 def test_media_retirement_pending_never_normal_closes(self):
  adapter=MediaAdapter(None,{},None,None,None);adapter.backend=Mock();adapter.backend.retire_world.return_value=False
  self.assertFalse(adapter.close(NS(epoch_valid=False)));adapter.backend.close.assert_not_called()
 def test_media_resume_ack_and_initial_false_are_not_completion(self):
  adapter=MediaAdapter(None,{},None,None,None)
  adapter.backend=Mock(state='open',audio_dependency=None);adapter.backend.resume.return_value=True
  adapter.backend.playback_status.return_value={'IsReady':True,'IsPlaying':False,'IsPaused':False}
  adapter.opening_deadline=100
  with patch('expedition33.cinematics.adapters.time.monotonic',return_value=1):
   self.assertEqual(adapter.poll().state,BackendState.ACTIVE)
   self.assertEqual(adapter.poll().state,BackendState.ACTIVE)
  with patch('expedition33.cinematics.adapters.time.monotonic',return_value=101):
   self.assertEqual(adapter.poll().state,BackendState.FAILED)
 def test_media_requires_observed_true_then_false(self):
  adapter=MediaAdapter(None,{},None,None,None);adapter.running=True;adapter.opening_deadline=100
  adapter.backend=Mock(state='open',audio_dependency=None)
  adapter.backend.playback_status.side_effect=[{'IsPlaying':True},{'IsPlaying':False,'IsPaused':False}]
  self.assertEqual(adapter.poll().state,BackendState.ACTIVE)
  self.assertEqual(adapter.poll().state,BackendState.COMPLETE)
 def test_retirement_capabilities_require_exact_integer_protocols(self):
  transport=NS(sequence_retirement_protocol=1,media_retirement_protocol=1,music_audio_retirement_protocol=1,retired_world_cleanup_protocol=1)
  self.assertTrue(title_retirement_available(transport));self.assertTrue(media_retirement_available(transport))
  transport.music_audio_retirement_protocol=True
  self.assertFalse(title_retirement_available(transport));self.assertFalse(media_retirement_available(transport))

class MusicRetirementTests(unittest.TestCase):
 def owner(self,state='armed'):
  from expedition33._music_audio_owner import NativeMusicAudioOwner
  transport=NS(music_audio_retirement_protocol=1,command=Mock())
  session=NS(_transport=transport,_check=Mock(),_abort_ownership=Mock())
  owner=NativeMusicAudioOwner(NS(_session=session,_audio_owners=[]));owner.state=state
  return owner,session
 def test_closed_audio_still_requests_reference_cleanup_and_preserves_pending(self):
  import struct
  owner,session=self.owner('closed');replies=iter(((407,0),(0,0)))
  def command(name,data):
   error,state=next(replies)
   return {'music_audio_packet':(data[:24]+struct.pack('<II',error,state)+data[32:]).hex()}
  session._transport.command.side_effect=command
  self.assertFalse(owner.retire_world());self.assertTrue(owner.retire_world())
  self.assertEqual([int.from_bytes(c.args[1][4:8],'little') for c in session._transport.command.call_args_list],[5,5])
  session._abort_ownership.assert_not_called()
 def test_unknown_retirement_never_aborts_unrelated_sdk(self):
  owner,session=self.owner();session._transport.command.side_effect=OSError('lost reply')
  with self.assertRaises(OSError):owner.retire_world()
  self.assertEqual(owner.state,'unknown');session._abort_ownership.assert_not_called()

class ScopeAdmissionTests(unittest.TestCase):
 def test_real_scope_rejects_missing_protocol_before_backend_construction(self):
  from expedition33._scope import SessionScope
  session=NS(_transport=NS())
  scope=SessionScope(session)
  from expedition33.cinematics.controller import StartResult
  self.assertEqual(TitleAdapter(scope,{},None,None).start(),StartResult.REJECTED)
  self.assertEqual(MediaAdapter(scope,{},None,None,None).start(),StartResult.REJECTED)

class SequenceDependentReceiptTests(unittest.TestCase):
 def sequence(self,ack):
  from expedition33.sequences import OwnedLevelSequence
  from expedition33._cinematic_widget import NativeCinematicWidgets
  scope=NS(_audio_owners=[])
  widget=NativeCinematicWidgets(scope);widget.state='armed'
  sequence=object.__new__(OwnedLevelSequence)
  sequence.state='prepared';sequence.owner=NS(_retirement_ack=ack,retire_world=lambda:True)
  sequence.scope=scope;sequence.planner=None;sequence._endpoint=None
  return sequence,widget
 def test_exact_receipt_releases_only_matching_widget_tracking_without_status_ipc(self):
  sequence,widget=self.sequence(True)
  widget.status=Mock(side_effect=AssertionError('No stale IPC'))
  with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):
   self.assertTrue(sequence.retire_world(closed_dependents=(widget,)))
  self.assertEqual(widget.state,'closed');self.assertEqual(sequence.scope._audio_owners,[])
  widget.status.assert_not_called()
 def test_missing_receipt_keeps_widget_owned(self):
  sequence,widget=self.sequence(False)
  with self.assertRaises(RuntimeError):sequence.retire_world(closed_dependents=(widget,))
  self.assertEqual(widget.state,'armed');self.assertIn(widget,sequence.scope._audio_owners)
