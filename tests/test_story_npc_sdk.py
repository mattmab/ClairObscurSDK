import struct
import unittest
from types import SimpleNamespace as N
from unittest.mock import patch,Mock
from expedition33 import _story_npc_wire as wire
from expedition33.story_npc import StoryNpc,decode,carrier_pose,visual_pose

class StoryNpcTests(unittest.TestCase):
    def named_speaker(self,*,warm=True):
        from contextlib import nullcontext
        npc=object.__new__(StoryNpc)
        def obj(index,**kw):return N(index=index,serial=1001+index,address=0x10000+index*16,**kw)
        npc.npc=obj(1);npc.speaker=obj(2);npc.system_cdo=obj(3)
        setter=obj(4);speaker=obj(5,class_name='BP_DataAsset_DialogueCharacter_C',outer_index=1)
        held=N(active=True,_token=55,object=speaker)
        created=N(return_value=speaker,_leases=(held,))
        npc._spawn_speaker=Mock(return_value=created)
        npc.actor=N(owner=N(_owner=42))
        catalog=N(find_path=Mock(return_value=setter))
        resources=N(load=Mock(return_value=obj(6)),hold=Mock(side_effect=lambda value:N(object=value)))
        construction=N(resources=resources,catalog=Mock(return_value=catalog))
        def command(name,packet):
            reply=bytearray(packet);struct.pack_into('<I',reply,12,1)
            return {'mesh_packet':bytes(reply).hex()}
        transport=N(command=Mock(side_effect=command))
        npc.scope=N(pid=123,_session=N(_transport=transport,_story_construction_resources=construction if warm else None),_lease_context=nullcontext)
        return npc,created,resources,catalog

    def test_named_speaker_uses_factory_output_lease_and_retained_title_metadata(self):
        npc,created,resources,catalog=self.named_speaker()
        with patch('expedition33._stable_lease.acquire_stable',side_effect=AssertionError('No duplicate leases')):
            npc._create_speaker('Renoir')
        self.assertIs(npc._speaker_result,created);self.assertIs(npc.speaker,created.return_value)
        self.assertEqual([c.args[0] for c in resources.hold.call_args_list],[npc.system_cdo,catalog.find_path.return_value])
        command=npc.scope._session._transport.command
        command.assert_called_once()
        self.assertEqual(struct.unpack_from('<Q',command.call_args.args[1],24)[0],55)
        self.assertFalse(npc._speaker_unknown)

    def test_missing_or_ambiguous_factory_ownership_never_names_the_speaker(self):
        for state in ('missing','expired','ambiguous','changed'):
            npc,created,resources,_=self.named_speaker()
            if state=='missing':created._leases=()
            elif state=='expired':created._leases[0].active=False
            elif state=='ambiguous':created._leases*=2
            else:created._leases[0].object=N(index=5,serial=2000,address=0x10050)
            with self.assertRaisesRegex(RuntimeError,'one retained factory output'):npc._create_speaker('Renoir')
            npc.scope._session._transport.command.assert_not_called();resources.hold.assert_not_called()
            self.assertIs(npc._speaker_result,created)

    def test_expired_title_metadata_never_dispatches_name_or_recreates_speaker(self):
        npc,created,resources,_=self.named_speaker()
        resources.hold.side_effect=RuntimeError('Metadata lease expired')
        with self.assertRaisesRegex(RuntimeError,'lease expired'):npc._create_speaker('Renoir')
        npc.scope._session._transport.command.assert_not_called();npc._spawn_speaker.assert_called_once()
        self.assertIs(npc._speaker_result,created)

    def test_naming_failure_keeps_exact_factory_lease_and_quarantines_owner(self):
        npc,created,resources,_=self.named_speaker()
        npc.scope._session._transport.command.side_effect=RuntimeError('ACK unavailable')
        with self.assertRaisesRegex(RuntimeError,'ACK unavailable'):npc._create_speaker('Renoir')
        self.assertTrue(npc._speaker_unknown);self.assertIs(npc._speaker_result,created)
        self.assertFalse(npc.close());self.assertFalse(npc.retire_world())

    def test_without_title_resources_factory_lease_is_reused_but_metadata_is_retained(self):
        npc,created,resources,catalog=self.named_speaker(warm=False)
        with patch('expedition33.catalog.capture_matching',return_value=catalog),patch('expedition33._stable_lease.acquire_stable',side_effect=lambda scope,value:(N(object=value),None)) as acquire:
            npc._create_speaker('Faceless Boy')
        self.assertEqual([c.args[1] for c in acquire.call_args_list],[npc.system_cdo,catalog.find_path.return_value])
        self.assertIs(npc.speaker,created.return_value)
        npc.scope._session._transport.command.assert_called_once()

    def test_prepare_reuses_just_validated_carrier_result_before_native_configuration(self):
        npc=object.__new__(StoryNpc);npc.state='new';npc.visual=None;npc._configure=Mock()
        actor=N(index=20,serial=3,address=0x20000)
        npc.actor=N(identity=(20,3,0x20000),prepared_actor=actor,prepare_story_npc=Mock())
        speaker=N(class_name='BP_DataAsset_DialogueCharacter_C')
        resources=N(load=Mock(side_effect=(speaker,object())))
        catalog=N(find_path=Mock(side_effect=[object() for _ in range(5)]))
        prepared=N(resources=resources,catalog=Mock(return_value=catalog))
        npc.scope=N(pid=123,_session=N(_story_construction_resources=prepared))
        with patch('expedition33.catalog.capture_selected',side_effect=AssertionError('Carrier was already checked')):
            self.assertEqual(npc.prepare((0.,0.,0.,1.,0.,0.,0.,0.,1.,1.,1.,0.),'/Game/Speaker.Speaker',visual_profile=None),(20,3,0x20000))
        self.assertIs(npc.npc,actor);self.assertEqual(npc.state,'prepared')
        npc._configure.assert_called_once_with(False)

    def test_ground_placement_keeps_native_player_marker_above_floor(self):
        feet=(0.,0.,0.,1.,100.,200.,300.,0.,1.,1.,1.,0.)
        self.assertEqual(carrier_pose(feet)[4:7],(100.,200.,388.))
        self.assertEqual(feet[6],300.)
        npc=object.__new__(StoryNpc);npc.state='visible';npc.actor=Mock();npc.visual=Mock()
        npc.move((100.,200.,300.),45.)
        npc.actor.move.assert_called_once_with((100.,200.,388.),45.,placement=True)
        npc.visual.move.assert_called_once_with((100.,200.,300.),-45.,placement=True)
    def test_visual_rig_forward_matches_placement_without_rotating_carrier(self):
        import math
        for yaw in (0.,45.,180.,-120.):
            half=math.radians(yaw)/2
            original=(0.,0.,math.sin(half),math.cos(half),1.,2.,3.,0.,1.,1.,1.,0.)
            visual=visual_pose(original);z,w=visual[2:4]
            # The rig's +Y axis now points along the carrier's +X axis.
            self.assertAlmostEqual(-2*z*w,math.cos(math.radians(yaw)))
            self.assertAlmostEqual(1-2*z*z,math.sin(math.radians(yaw)))
            self.assertEqual(visual[4:],original[4:])
            self.assertEqual(carrier_pose(original)[:4],original[:4])
    def test_original_character_visual_uses_source_capsule_center_and_facing(self):
        feet=(0.,0.,1.,0.,100.,200.,300.,0.,1.,1.,1.,0.)
        for profile in ('clea-spirit','renoir-spirit','sophie'):
            visual=visual_pose(feet,profile)
            self.assertEqual(visual[:4],feet[:4]);self.assertEqual(visual[4:7],(100.,200.,388.))
            npc=object.__new__(StoryNpc);npc.state='visible';npc.actor=Mock();npc.visual=Mock(profile=profile)
            npc.move((100.,200.,300.),45.)
            npc.visual.move.assert_called_once_with((100.,200.,388.),45.,placement=True)
        self.assertEqual(visual_pose(feet,'faceless-boy')[4:7],(100.,200.,300.))
    def packet(self,activate=False):
        objects=[N(index=i,serial=i+1,address=0x10000+i*16) for i in range(8)]
        return wire.encode(123,*objects[:4],objects[4:],activate=activate)
    def test_fixed_input_packet_and_ack_preserve_actor_and_class_identities(self):
        for activate in (False,True):
            packet=self.packet(activate);wire.validate_request(packet)
            response=bytearray(packet);struct.pack_into('<I',response,12,1);decode(packet,bytes(response))
            for at in (16,24,40,56,72,88,152,156):
                bad=bytearray(response);bad[at]^=1
                with self.assertRaises(RuntimeError):decode(packet,bytes(bad))
    def test_invalid_actor_identity_activation_and_padding_are_rejected(self):
        for at,value in ((0,4),(4,229),(12,1),(24,0xffffffff),(32,1),(152,2),(156,1)):
            packet=bytearray(self.packet());struct.pack_into('<I',packet,at,value)
            with self.assertRaises(ValueError):wire.validate_request(bytes(packet))
    def test_old_runtime_rejects_before_constructing_an_actor(self):
        for cap in (0,True,2):
            scope=N(_check=lambda:None,_session=N(_transport=N(story_npc_blueprint_protocol=cap)))
            with patch('expedition33.cinematics.blueprint_actor.BlueprintActor') as actor:
                with self.assertRaises(RuntimeError):StoryNpc(scope)
                actor.assert_not_called()

    def test_failed_visual_reveal_never_enables_original_interaction(self):
        npc=object.__new__(StoryNpc);npc.state='prepared';npc.actor=Mock();npc.visual=Mock()
        npc.scope=N(_session=N(_transport=N()))
        npc.visual.reveal.side_effect=RuntimeError('visual unavailable');npc._configure=Mock()
        with self.assertRaises(RuntimeError):npc.reveal()
        npc._configure.assert_not_called();self.assertEqual(npc.state,'failed')
        with self.assertRaises(RuntimeError):npc.reveal()
        npc.actor.reveal.assert_called_once()

    def test_presentation_reveal_never_activates_interaction_or_visual(self):
        npc=object.__new__(StoryNpc);npc.state='prepared';npc.actor=Mock(identity=(1,2,0x10000));npc.visual=Mock()
        npc._configure=Mock()
        with patch.object(npc,'set_interaction_enabled') as gate:npc.reveal_presentation()
        gate.assert_called_once_with(False);npc._configure.assert_not_called();npc.visual.reveal.assert_not_called()
        self.assertEqual(npc.state,'visible');self.assertTrue(npc._presentation_only_reveal)
        with self.assertRaisesRegex(RuntimeError,'cannot enable'):npc.set_interaction_enabled(True)
        with self.assertRaises(RuntimeError):npc.reveal_presentation()
        npc.actor.reveal.assert_called_once()

    def test_carrier_only_move_preserves_hidden_visual_and_failure_is_not_retried(self):
        npc=object.__new__(StoryNpc);npc.state='visible';npc.actor=Mock();npc.visual=Mock()
        npc.move((100.,200.,300.),45.,visual=False)
        npc.actor.move.assert_called_once_with((100.,200.,388.),45.,placement=True)
        npc.visual.move.assert_not_called()
        with self.assertRaises(TypeError):npc.move((1,2,3),4,visual=1)
        npc.actor.move.side_effect=RuntimeError('placement uncertain')
        with self.assertRaises(RuntimeError):npc.move((1,2,3),4,visual=False)
        self.assertEqual(npc.state,'failed')
        with self.assertRaises(RuntimeError):npc.move((1,2,3),4,visual=False)
        self.assertEqual(npc.actor.move.call_count,2)
    def test_pending_visual_cleanup_keeps_the_interaction_carrier_owned(self):
        npc=object.__new__(StoryNpc);npc.state='visible';npc.actor=Mock();npc.visual=Mock()
        npc.visual.retire_world.return_value=False
        self.assertFalse(npc.retire_world());npc.actor.retire_world.assert_not_called()
        npc.visual.retire_world.return_value=True;npc.actor.retire_world.return_value=True
        self.assertTrue(npc.retire_world());self.assertEqual(npc.state,'closed')

    def test_speaker_factory_uses_fresh_selected_results_without_replaying_creation(self):
        npc=object.__new__(StoryNpc)
        objects=[N(index=i,serial=1001+i,address=0x10000+i*16) for i in range(4)]
        library,function,cls,npc.npc=objects
        catalog=Mock();catalog.find_path.side_effect=[library,function]
        plan=Mock();planner=Mock();planner.prepare.return_value=plan
        npc.scope=N(pid=123,invocation_planner=Mock(return_value=planner))
        with patch('expedition33.catalog.capture_selected',return_value='selected') as capture:
            self.assertIs(npc._spawn_speaker(catalog,cls),plan.invoke.return_value)
        capture.assert_called_once_with(123,tuple((o.index,o.serial,o.address) for o in objects))
        npc.scope.invocation_planner.assert_called_once_with(selected_results=True,catalog='selected')
        plan.invoke.assert_called_once_with(fresh_results=True)
        catalog.find_path.side_effect=[library,function]
        plan.invoke.side_effect=RuntimeError('Result exposure failed after dispatch')
        with patch('expedition33.catalog.capture_selected',return_value='selected'):
            with self.assertRaises(RuntimeError):npc._spawn_speaker(catalog,cls)
        self.assertEqual(plan.invoke.call_count,2)

    def test_warm_speaker_factory_still_recaptures_current_outer_and_never_replays(self):
        npc=object.__new__(StoryNpc)
        objects=[N(index=i,serial=1001+i,address=0x10000+i*16) for i in range(4)]
        library,function,cls,npc.npc=objects
        catalog=Mock();catalog.find_path.side_effect=[library,function]
        construction=Mock();planner=construction.movement_planner.return_value
        npc.scope=N(pid=123,_session=N(_story_construction_resources=construction),invocation_planner=Mock())
        with patch('expedition33.catalog.capture_selected',return_value='fresh') as read:
            npc._spawn_speaker(catalog,cls)
        read.assert_called_once_with(123,tuple((o.index,o.serial,o.address) for o in objects))
        construction.movement_planner.assert_called_once_with(npc.scope,'fresh')
        npc.scope.invocation_planner.assert_not_called()
        planner.prepare.assert_called_once_with(library,function,ObjectClass=cls,Outer=npc.npc)
        planner.prepare.return_value.invoke.assert_called_once_with(fresh_results=True)
        catalog.find_path.side_effect=[library,function]
        construction.movement_planner.reset_mock()
        with patch('expedition33.catalog.capture_selected',side_effect=RuntimeError('outer retired')):
            with self.assertRaisesRegex(RuntimeError,'outer retired'):npc._spawn_speaker(catalog,cls)
        construction.movement_planner.assert_not_called()

