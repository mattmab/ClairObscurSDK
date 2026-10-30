from contextlib import nullcontext
from dataclasses import FrozenInstanceError
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from expedition33 import _paired_phase_observation as phase
from expedition33.values import StoredStruct


def struct(**fields):
    return StoredStruct(None, MappingProxyType(fields), {}, {}, False)


class PairPhaseObservationTests(unittest.TestCase):
    def test_states_never_claim_visual_acceptance(self):
        args = dict(requested_id=phase.CINEMATIC_ID, is_cinematic=True,
                    sequence_started=True, actor=(1, 2, 3), player=(4, 5, 6), asset_path=phase.SEQUENCE)
        self.assertEqual(phase.classify(**args), 'pair_sequence_started')
        for field, value, state in (
            ('requested_id', 'DuallistPhase2', 'other_or_idle'),
            ('is_cinematic', False, 'pair_requested_not_active'),
            ('player', None, 'pair_preparing'),
            ('asset_path', '/Game/Unrelated', 'pair_asset_mismatch'),
            ('sequence_started', False, 'pair_sequence_not_started')):
            self.assertEqual(phase.classify(**dict(args, **{field: value})), state)
        with self.assertRaises(ValueError):
            phase.classify(**dict(args, is_cinematic=1))

    def setup_sample(self):
        def obj(index, name, **extra):
            return SimpleNamespace(index=index, serial=1, address=0x10000+index*0x100,
                class_name=name, object_flags=0, **extra)
        self.world = obj(1, 'World')
        self.system = obj(2, 'BP_CinematicSystem_C', class_index=20)
        self.actor = obj(3, 'LevelSequenceActor')
        self.player = obj(4, 'LevelSequencePlayer', outer_index=3, outer_serial=1)
        self.asset = obj(5, 'LevelSequence')
        self.controller = obj(6, 'PlayerController')
        self.manager = obj(7, 'PlayerCameraManager')
        self.camera = obj(8, 'CineCameraActor', class_index=21)
        self.catalog = Mock()
        self.catalog.objects = [self.system]
        self.catalog.by_index = {x.index:x for x in (self.world,self.system,self.actor,
            self.player,self.asset,self.controller,self.manager,self.camera)}
        self.catalog.by_index.update({20: 'system-class', 21: 'camera-class'})
        self.catalog.path_name.side_effect = lambda x: {
            id(self.asset):phase.SEQUENCE, id('system-class'):phase.SYSTEM_CLASS,
            id('camera-class'):'/Script/CinematicCamera.CineCameraActor'}[id(x)]
        self.catalog.outer_chain.return_value = [self.world]
        self.catalog.with_observations.return_value = self.catalog
        self.scope = Mock()
        self.scope.pid = 100
        self.context = dict(world=(100,1,1,0x10100),controller=(100,6,1,0x10600),world_path='/Game/World.World')
        self.values = {
            2: dict(CurrentTriggerCinematicParameters=struct(**{phase.ID_FIELD:phase.CINEMATIC_ID}),
                    IsPlayingCinematic=True, SequenceStarted=True,
                    LevelSequencePlayerActor=self.actor,LevelSequencePlayer=self.player),
            3: dict(SequencePlayer=self.player,LevelSequenceAsset=self.asset),
            4: dict(Sequence=self.asset,Status=1),
            6: dict(PlayerCameraManager=self.manager),
            7: dict(ViewTarget=struct(Target=self.camera)),
        }

    def patches(self, contexts=None):
        self.setup_sample()
        def read(catalog, obj, *, fields):
            fields = {k:v for k,v in self.values[obj.index].items() if k in fields}
            return SimpleNamespace(values={(obj.index,k):v for k,v in fields.items()},
                                   errors={},truncated=frozenset()), self.catalog
        return (patch.object(phase,'ReadBatch',return_value=nullcontext()),
                patch.object(phase,'capture_matching',return_value=self.catalog),
                patch.object(phase,'capture_selected',return_value=self.catalog),
                patch.object(phase,'controller_context',side_effect=contexts or [self.context,self.context]),
                patch.object(phase,'read_values_with_references',side_effect=read))

    def test_exact_active_sequence_and_camera_are_copied_without_calls(self):
        patches = self.patches()
        with patches[0], patches[1] as matching, patches[2], patches[3], patches[4]:
            sample = phase.observe(self.scope, expected_context=self.context)
        matching.assert_called_once_with(100,classes=('BP_CinematicSystem_C',))
        self.assertEqual(sample.asset_path,phase.SEQUENCE)
        self.assertEqual(sample.state,'pair_sequence_started')
        self.assertEqual(sample.camera_target,phase._id(self.camera))
        self.scope._session._transport.command.assert_not_called()
        with self.assertRaises(FrozenInstanceError):
            sample.state = 'visible'

    def test_world_change_and_mismatched_player_reject(self):
        patches = self.patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            self.player.outer_serial = 2
            with self.assertRaisesRegex(RuntimeError,'outside its actor'):
                phase.observe(self.scope)
        patches = self.patches()
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            with self.assertRaisesRegex(RuntimeError,'before observation'):
                phase.observe(self.scope,expected_context={})
        patches = self.patches()
        with patches[0], patches[1], patches[2], patches[3] as context, patches[4]:
            context.side_effect = [self.context, dict(self.context,world=(100,99,1,0x99999))]
            with self.assertRaisesRegex(RuntimeError,'during observation'):
                phase.observe(self.scope)

    def test_missing_struct_or_truncated_field_never_invents_value(self):
        for value in (None,struct(),StoredStruct(None,{phase.ID_FIELD:phase.CINEMATIC_ID},{},{},True)):
            with self.assertRaises(RuntimeError):
                phase._struct_field(value,phase.ID_FIELD)


if __name__ == '__main__':
    unittest.main()
