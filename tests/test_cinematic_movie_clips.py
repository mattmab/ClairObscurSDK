import unittest
from expedition33.cinematics.movie_clips import installed_movie_clips, clip_path
from expedition33.cinematics.browser_view import _capabilities


class InstalledMovieTests(unittest.TestCase):
    MANIFEST = b'Sandfall/Content/Movies/CS_Test Scene.mp4\t2025-01-01\n'

    def test_clips_do_not_fabricate_save_unlock_or_full_scene(self):
        row, = installed_movie_clips(self.MANIFEST, available=True, gameplay=True)
        self.assertIsNone(row['unlocked'])
        self.assertIsNone(row['saved_id'])
        self.assertFalse(row['full_scene'])
        self.assertEqual(_capabilities(row), (1, 4))
        self.assertEqual(clip_path(row), './Movies/CS_Test Scene.mp4')

    def test_requires_native_support_and_loaded_gameplay(self):
        for available, gameplay in ((False, True), (True, False), (False, False)):
            row, = installed_movie_clips(self.MANIFEST, available=available, gameplay=gameplay)
            self.assertEqual(_capabilities(row), ())

    def test_ignores_unrelated_assets_and_nested_or_traversal_paths(self):
        self.assertEqual(installed_movie_clips(b'Other/CS_Test.mp4\nSandfall/Content/Movies/CS_../x.mp4\n'
            b'Sandfall/Content/Movies/CS_../x.mp4\nSandfall/Content/Movies/CS_..mp4\n'), [])

    def test_duplicate_identity_rejected(self):
        with self.assertRaises(ValueError):
            installed_movie_clips(self.MANIFEST * 2)

    def test_manifest_revision_changes_admission_signature(self):
        a, = installed_movie_clips(self.MANIFEST)
        b, = installed_movie_clips(self.MANIFEST.replace(b'2025', b'2026'))
        self.assertNotEqual(a['definition_sha256'], b['definition_sha256'])

    def test_arbitrary_file_cannot_be_requested_as_clip(self):
        for identity in ('C:/secret.mp4', 'installed-movie:Sandfall/Content/Movies/../../secret.mp4'):
            with self.assertRaises(ValueError):
                clip_path(dict(id=identity, replay_kind='movie_clip'))

    def test_clip_filter_and_details_do_not_label_clip_as_locked(self):
        from types import SimpleNamespace as N
        from unittest.mock import Mock
        from expedition33.cinematics.browser_view import BrowserView
        row, = installed_movie_clips(self.MANIFEST, available=True, gameplay=True)
        model = N(library=(row, dict(id='story', title='Story', supported=False)), filter='clips')
        view = BrowserView(N(_check=Mock()), model)
        self.assertEqual(tuple(r['id'] for r in view.scenes()), (row['id'],))
        frame = view.render()
        detail = view.activate(frame.revision, 100)
        self.assertIn('save unlock not required', detail.description)

    def test_full_scene_filter_offers_original_action_instead_of_movie_segment(self):
        from types import SimpleNamespace as N
        from unittest.mock import Mock
        from expedition33.cinematics.browser_view import BrowserView
        movie=dict(id='movie',title='Scene',reason='Movie segment',replay_kind='movie',
                   supported=True,unlocked=True,original_supported=True,original_destination='/Game/Exact.World')
        view=BrowserView(N(_check=Mock()),N(library=(movie,),filter='full'))
        frame=view.render();detail=view.activate(frame.revision,100)
        self.assertEqual(tuple(c.token for c in detail.controls),(13,9,6))
        self.assertIn('authored actors, lighting and audio',detail.description)


if __name__ == '__main__':
    unittest.main()
