from contextlib import nullcontext
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33 import RuntimeQueryError
from expedition33._original_trigger_fight import OriginalTriggerFight, _GEOMETRY, _pose


def obj(index, **kwargs):
    return N(index=index, serial=1, address=index * 100, **kwargs)


def stored(fields):
    return N(fields=fields, errors={}, truncated=False)


class OriginalArenaFrameBatchTests(unittest.TestCase):
    def setUp(self):
        self.actor = obj(1, class_index=2)
        self.actor_class = obj(2)
        self.component_class = obj(3)
        self.child_class = obj(4)
        self.template = obj(5)
        self.setter, self.getter = obj(6), obj(7)
        self.components = [obj(10 + i, outer_index=1, outer_serial=1, class_index=3) for i in range(20)]
        self.children = [obj(50 + i, class_index=4) for i in range(14)]
        self.names = ['DefaultSceneRoot', *(f'Component{i}' for i in range(1, 20))]
        self.actor_values = dict(zip(self.names, self.components))
        self.actor_values['RootComponent'] = self.components[0]
        self.rows = {}
        zero = dict(X=0., Y=0., Z=0.)
        rotation = dict(Pitch=0., Yaw=0., Roll=0.)
        scale = dict(X=1., Y=1., Z=1.)
        frames = {}
        children = {}
        for i, (name, component) in enumerate(zip(self.names, self.components)):
            frames[name] = dict(class_path='Component', parent_field=None if i == 0 else self.names[0],
                                location=zero.copy(), rotation=rotation.copy(), scale=scale.copy(), socket='None')
            self.rows[component.index] = dict(AttachParent=None if i == 0 else self.components[0],
                AttachSocketName='None', RelativeLocation=stored(zero.copy()),
                RelativeRotation=stored(rotation.copy()), RelativeScale3D=stored(scale.copy()))
            if 1 <= i <= 14:
                child = self.children[i - 1]
                self.rows[component.index].update(ChildActor=child, ChildActorClass=self.child_class,
                                                  ChildActorTemplate=self.template)
                children[name] = dict(class_path='Child', template_path='Template')
                if i <= 7:
                    children[name]['slot_index'] = i - 1
                    self.rows[child.index] = {'SlotIndex': i - 1}
        objects = [self.actor, self.actor_class, self.component_class, self.child_class, self.template,
                   self.setter, self.getter, *self.components, *self.children]
        paths = {2: 'Arena', 3: 'Component', 4: 'Child', 5: 'Template',
                 6: '/Script/Engine.SceneComponent:K2_SetRelativeTransform',
                 7: '/Script/Engine.SceneComponent:GetRelativeTransform'}
        self.catalog = N(by_index={o.index: o for o in objects}, objects=objects,
                         path_name=lambda o: paths.get(o.index, 'actor' + str(o.index)))
        self.catalog.with_observations = lambda other: self.catalog
        self.fight = OriginalTriggerFight.__new__(OriginalTriggerFight)
        self.fight.recipe = {'arena': dict(class_path='Arena', frames=frames, children=children)}
        self.fight._scope = N(pid=7)
        self.fight._arena = N(actor_identity=(1, 1, 100), set_component_pose_once=Mock(return_value='ACK'))
        self.fight._assembly = {}
        self.fight._idle = Mock()
        self.fight._batch = lambda: nullcontext()
        self.pose = _pose(zero, rotation, scale)
        self.read_batches = []
        self.corrupt = None

    def read_many(self, catalog, objects, *, fields):
        objects = tuple(objects)
        self.read_batches.append((tuple(o.index for o in objects), fields))
        result = {o.index: N(values={(i, name): self.rows[o.index][name] for i, name in enumerate(fields)},
                             errors={}, truncated=False) for o in objects}
        if self.corrupt:
            self.corrupt(result, fields)
        return result, catalog

    def run_frames(self, *, corrections=False):
        with (patch('expedition33.catalog.capture_selected', return_value=self.catalog),
              patch('expedition33.catalog.capture_matching', return_value=self.catalog),
              patch('expedition33.enemy_spawning._fields', return_value=(self.actor_values, self.catalog)) as one,
              patch('expedition33.values.read_values_many_with_references', side_effect=self.read_many)):
            result = self.fight._arena_frames(self.pose, allow_corrections=corrections)
            self.assertEqual(one.call_count, 1)
            return result

    def test_all_fresh_geometry_children_and_slots_use_three_bounded_batches(self):
        self.assertEqual(self.run_frames(), [])
        self.assertEqual([(len(ids), fields) for ids, fields in self.read_batches],
                         [(20, _GEOMETRY), (14, ('ChildActor', 'ChildActorClass', 'ChildActorTemplate')),
                          (7, ('SlotIndex',))])
        self.assertEqual(self.fight._assembly['frames_observed'], 20)
        self.assertEqual(len(self.fight._assembly['children']), 14)
        self.assertTrue(self.fight._assembly['frames_verified'])
        self.fight._arena.set_component_pose_once.assert_not_called()

    def test_second_pass_rereads_and_rejects_changed_slot(self):
        self.run_frames()
        self.rows[self.children[3].index]['SlotIndex'] = 9
        with self.assertRaisesRegex(RuntimeError, 'slot index differs'):
            self.run_frames()
        self.assertEqual(len(self.read_batches), 6)
        self.fight._arena.set_component_pose_once.assert_not_called()

    def test_foreign_component_is_rejected_before_any_batch_or_mutation(self):
        self.components[8].outer_serial = 2
        with self.assertRaisesRegex(RuntimeError, 'ownership/class differs'):
            self.run_frames(corrections=True)
        self.assertFalse(self.read_batches)
        self.fight._arena.set_component_pose_once.assert_not_called()

    def test_incomplete_or_failed_batches_cannot_apply_corrections(self):
        self.rows[self.components[4].index]['RelativeLocation'].fields['X'] = 10.
        def missing(result, fields):
            result.pop(next(iter(result)))
        def truncated(result, fields):
            next(iter(result.values())).truncated = True
        def error(result, fields):
            next(iter(result.values())).errors = {'read': 'failed'}
        def missing_field(result, fields):
            next(iter(result.values())).values.popitem()
        for corruption in (missing, truncated, error, missing_field):
            with self.subTest(corruption=corruption.__name__):
                self.corrupt = corruption
                with self.assertRaisesRegex(RuntimeError, 'Incomplete original arena'):
                    self.run_frames(corrections=True)
                self.fight._arena.set_component_pose_once.assert_not_called()

    def test_child_ownership_template_and_duplicate_guards_remain(self):
        original = self.rows[self.components[5].index].copy()
        changes = ({'ChildActor': None}, {'ChildActorClass': obj(99)},
                   {'ChildActorTemplate': self.component_class}, {'ChildActor': self.children[0]})
        for change in changes:
            with self.subTest(change=change):
                self.rows[self.components[5].index] = dict(original, **change)
                with self.assertRaisesRegex(RuntimeError, 'child/template differs'):
                    self.run_frames(corrections=True)
                self.fight._arena.set_component_pose_once.assert_not_called()

    def test_correction_only_occurs_after_complete_slot_validation_and_idle_check(self):
        self.rows[self.components[4].index]['RelativeLocation'].fields['X'] = 10.
        self.run_frames(corrections=True)
        self.assertEqual(len(self.read_batches), 3)
        self.fight._idle.assert_called_once_with()
        self.fight._arena.set_component_pose_once.assert_called_once_with(
            self.components[4], self.setter, self.getter, self.pose)
        self.assertEqual(self.fight._assembly['corrections'][self.names[4]], 'ACK')
        self.assertFalse(self.fight._assembly['frames_verified'])
        with self.assertRaisesRegex(RuntimeError, 'frame verification failed'):
            self.run_frames()
        self.assertEqual(self.fight._arena.set_component_pose_once.call_count, 1)

    def test_stale_generation_read_failure_propagates_without_correction(self):
        def stale(*args):
            raise RuntimeQueryError('Selected identity changed')
        self.corrupt = stale
        with self.assertRaises(RuntimeQueryError):
            self.run_frames(corrections=True)
        self.fight._arena.set_component_pose_once.assert_not_called()


if __name__ == '__main__':
    unittest.main()
