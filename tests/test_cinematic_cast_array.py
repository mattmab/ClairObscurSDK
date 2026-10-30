from types import SimpleNamespace
import unittest

from expedition33.values import _array_prefix_limits


class CinematicCastArrayTests(unittest.TestCase):
    def test_only_exact_cast_owner_field_and_struct_allow_larger_prefix(self):
        owner, struct = object(), object()
        paths = {owner: '/Script/MovieScene.MovieScene'}
        catalog = SimpleNamespace(by_index={1: owner}, path_name=paths.__getitem__)
        for field, inner in (('Spawnables', 'MovieSceneSpawnable'),
                             ('Possessables', 'MovieScenePossessable'),
                             ('ObjectBindings', 'MovieSceneBinding')):
            paths[struct] = '/Script/MovieScene.' + inner
            self.assertEqual(_array_prefix_limits(catalog, 1, field, 'StructProperty', struct), (64, 256, 4096))
            self.assertEqual(_array_prefix_limits(catalog, 1, field, 'ObjectProperty', struct), (64, 256))
            self.assertEqual(_array_prefix_limits(catalog, 2, field, 'StructProperty', struct), (64, 256))
            paths[struct] = '/Game/Other.' + inner
            self.assertEqual(_array_prefix_limits(catalog, 1, field, 'StructProperty', struct), (64, 256))
        paths[struct] = '/Script/MovieScene.MovieSceneBinding'
        self.assertEqual(_array_prefix_limits(catalog, 1, 'Tracks', 'StructProperty', struct), (64, 256))
        paths[owner] = '/Game/Other.MovieScene'
        self.assertEqual(_array_prefix_limits(catalog, 1, 'ObjectBindings', 'StructProperty', struct), (64, 256))
