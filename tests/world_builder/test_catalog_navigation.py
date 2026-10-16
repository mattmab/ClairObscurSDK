import unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch
from test_camera_settings import CatalogMenu
from camera_test_builder.library import Library
from camera_test_builder.mod import Mod

class CatalogNavigationTests(unittest.TestCase):
    def test_menu_worker_is_reused_and_failed_worker_is_not_restarted(self):
        mod=Mod();mod.session=SimpleNamespace(pid=123)
        worker=Mock();worker.bind.side_effect=lambda:nullcontext(worker)
        with patch('camera_test_builder.mod.active_reader',return_value=None),patch('camera_test_builder.mod.ReadBatch',return_value=worker) as factory:
            with mod.menu_reads() as first:self.assertIs(first,worker)
            with mod.menu_reads() as second:self.assertIs(second,worker)
            factory.assert_called_once_with(123,share=True)
            worker.bind.side_effect=RuntimeError('reader closed')
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError,'reader closed'):
                    with mod.menu_reads():pass
            self.assertEqual(factory.call_count,1)

    def test_menu_worker_borrows_existing_context_only_for_same_process(self):
        mod=Mod();mod.session=SimpleNamespace(pid=123)
        active=Mock(pid=123)
        with patch('camera_test_builder.mod.active_reader',return_value=active):
            with mod.menu_reads() as reader:self.assertIs(reader,active)
            self.assertIsNone(mod._menu_reader)
            active.pid=456
            with self.assertRaisesRegex(RuntimeError,'another process'):
                with mod.menu_reads():pass
    def test_image_batch_checks_underlying_session_capability(self):
        menu=object.__new__(CatalogMenu);token=object();menu.paint_batch=Mock(return_value=token)
        menu.scope=SimpleNamespace(_session=SimpleNamespace(_transport=SimpleNamespace(layout_batch_protocol=3)))
        self.assertIs(menu.image_batch(),token)
        menu.scope._session._transport.layout_batch_protocol=2
        self.assertIsInstance(menu.image_batch(),nullcontext)
    def test_navigation_hides_old_images_without_releasing_cached_brushes(self):
        menu=object.__new__(CatalogMenu)
        menu.images=[1,2];menu.image=3;menu.collapsed='hidden'
        menu.pending=['old'];menu.image_queue=['old'];menu.displayed={0:'old'}
        menu.thumbnails={'old':object()};menu._render_call=Mock()
        menu.paint_batch=lambda:nullcontext()
        menu.clear_images()
        self.assertEqual(menu.image_queue,[])
        self.assertEqual(menu.displayed,{})
        self.assertIn('old',menu.thumbnails)
        self.assertEqual([c.args[2] for c in menu._render_call.call_args_list],['SetVisibility']*3)

    def test_purge_drops_brushes_before_releasing_native_textures(self):
        menu=object.__new__(CatalogMenu)
        menu.images=[1];menu.collapsed='hidden';menu.displayed={};menu.thumbnails={'old':object()}
        events=[];menu._render_call=lambda obj,owner,name,**kw:events.append(name)
        menu.paint_batch=menu.image_batch=lambda:nullcontext()
        menu.cancel_preview=lambda:events.append('cancel')
        menu.mod=SimpleNamespace(started=True,scene_command=lambda op:events.append(op))
        menu.clear_images(purge=True)
        self.assertEqual(events,['SetVisibility','SetBrushResourceObject','cancel',39])
        self.assertFalse(menu.thumbnails)

    def test_cached_paths_repopulate_after_level_change_without_live_identities(self):
        library=object.__new__(Library)
        library.rows=[];library.known={};library.registry_paths=['/Game/Z.Z','/Game/A.A']
        library.seed_cached_catalog()
        self.assertEqual([r['name'] for r in library.rows],['A','Z'])
        self.assertEqual(set(library.known),set(library.registry_paths))
        self.assertTrue(all(set(r)=={'path','name','kind','source'} for r in library.rows))
        library.rows.append({'name':'live actor'})
        library.seed_cached_catalog()
        self.assertEqual(len(library.rows),3)
