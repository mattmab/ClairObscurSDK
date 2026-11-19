import importlib,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import test_story_packs

skin=importlib.import_module('story_packs_test.skin')


class StorySkinTests(unittest.TestCase):
    def test_art_is_noninteractive_and_unused_images_collapse(self):
        p=N(story_skin_back=99,story_skin_images=list(range(8)),story_skin_slots=list(range(8)),
            invisible=4,collapsed=1,position=Mock())
        dispatch=Mock()
        skin.paint(p,[((10,20,300,40),(1.,.9,.7,1.))],dispatch)
        self.assertEqual(p.position.call_count,3)
        dispatch.assert_any_call(0,'Widget','SetVisibility',InVisibility=4)
        dispatch.assert_any_call(2,'Widget','SetVisibility',InVisibility=4)
        dispatch.assert_any_call(4,'Widget','SetVisibility',InVisibility=1)
        _,x,y,w,h=p.position.call_args.args
        self.assertAlmostEqual(x+.055*w,10)
        self.assertAlmostEqual(y+.16*h,20)
        self.assertAlmostEqual(w*.88,300)
        self.assertAlmostEqual(h*.64,40)

    def test_standard_skin_removes_stock_chrome_and_tracks_row_geometry(self):
        def obj(i):return N(index=i,serial=1,address=i*16)
        slots=[obj(i) for i in range(10,16)]
        p=N(background=obj(1),surfaces=[obj(2),obj(3)],buttons=[obj(4)],
            title=obj(8),set_text=Mock(),surface_slots=slots[:2],button_slots=[slots[2]],scroll_slot=slots[3],
            row_slots=[slots[4]],_visible={0:True},direct=Mock(),_slot_geometry={})
        for slot,rect in zip(slots,[(32,182,596,760),(650,182,1238,760),
                (0,2,546,72),(52,250,556,672),(0,80,546,72)]):
            p._slot_geometry[(slot.index,slot.serial,slot.address)]=rect
        menu=N(panel=p,frame=N(controls=[N(label='Dialogue',enabled=True)]))
        from unittest.mock import patch
        with patch.object(skin,'paint') as paint:
            skin.paint_standard(menu)
        p.direct.assert_any_call(p.background,'Widget','SetRenderOpacity',InOpacity=0.)
        p.direct.assert_any_call(p.buttons[0],'Widget','SetRenderOpacity',InOpacity=0.)
        self.assertEqual(paint.call_args.args[1][0][0],(48,329,554,78))
        self.assertTrue(p._graph_active)


class LoadingSkinTests(unittest.TestCase):
    def test_only_prepares_detached_shared_panel_and_never_closes_its_owner(self):
        panel=N(state='open',scope=N(pid=1,_session=N(_transport=N(_executable='reader'))))
        session=N(_native_menu_service=N(menu=N(panel=panel)))
        owner=skin.LoadingSkin(session)
        from contextlib import nullcontext
        with patch.object(skin,'prepare') as prepare,patch('expedition33._reader.shared_operation',return_value=nullcontext()):
            owner.prepare(N(gi=(1,2,3)));prepare.assert_not_called()
            panel.state='built';owner.bind(N(gi=(1,2,3)),preparing=True)
            prepare.assert_called_once_with(panel)
            owner.close();owner.bind(N(gi=(1,2,3)))
            self.assertEqual(prepare.call_count,1);self.assertEqual(panel.state,'built')

    def test_ready_skin_does_not_reopen_reader_on_each_bind(self):
        panel=N(state='built',story_skin_ready=True)
        owner=skin.LoadingSkin(N(_native_menu_service=N(menu=N(panel=panel))))
        with patch.object(skin,'prepare') as prepare,patch('expedition33._reader.shared_operation') as reader:
            owner.bind(N());owner.observe_title(N())
            prepare.assert_not_called();reader.assert_not_called()
