import copy,importlib,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
import test_story_runtime as fixtures
from test_story_native_flow import Driver,NativeFlow
from test_story_view import StoryView
editor=importlib.import_module('story_packs_test.conversation_editor')

class ConversationEditorTests(unittest.TestCase):
    setUp=fixtures.StoryRuntimeTests.setUp
    def view(self):
        self.runtime.reconcile(fixtures.WORLD,(1,),ready=True)
        driver=Driver();driver.replace_presentation=Mock(return_value=19)
        flow=NativeFlow(self.runtime,driver);flow.interact([10,20,30])
        pack=copy.deepcopy(self.runtime.document)
        model=N(preview=N(flow=flow),live=N(choices=lambda:None,error=None),library=N(get=lambda _:pack))
        view=StoryView(N(_check=lambda:None),model);editor.open_editor(view)
        return view,flow,pack
    def test_open_uses_current_line_and_menu_order_without_advancing(self):
        view,flow,pack=self.view();before=copy.deepcopy(self.state.get(self.key))
        frame=view.render();labels=[c.label for c in frame.controls]
        self.assertTrue(any(s.startswith('Response 1: Tell me') for s in labels))
        self.assertTrue(any(s.startswith('Response 2: I will') for s in labels))
        self.assertTrue(flow.editing);self.assertEqual(self.state.get(self.key),before)
    def test_resume_redisplays_changed_graph_and_releases_hold(self):
        view,flow,pack=self.view();pack['dialogues']['first-meeting']['nodes']['welcome']['text']='Changed'
        frame=view.render();control=next(c for c in frame.controls if c.label=='Resume conversation')
        result=view.activate(frame.revision,control.token)
        self.assertTrue(result.closed);self.assertFalse(flow.editing)
        self.assertEqual(flow.view['text'],'Changed')
    def test_replaced_flow_rejects_editor_instead_of_editing_other_npc(self):
        view,flow,pack=self.view();view.model.preview.flow=N(stage='lines',view=flow.view,runtime=flow.runtime)
        with self.assertRaisesRegex(ValueError,'changed'):editor.rows(view)
    def test_no_owned_custom_conversation_is_a_clear_error(self):
        with self.assertRaisesRegex(ValueError,'Start a custom'):editor.active(N(preview=None,live=None))

    def test_pending_preview_cleanup_keeps_owner_without_failing_sdk_poll(self):
        Mod=importlib.import_module('story_packs_test.mod').Mod
        mod=Mod();mod.poll_fast=lambda:None
        preview=N(flow=N(stage=None),error=None,poll=lambda:None,close=Mock(return_value=False))
        mod.preview=preview;mod._test_pack='test';mod._test_dialogue='dialogue';mod._test_started=True
        mod.poll()
        self.assertIs(mod.preview,preview);self.assertFalse(mod.want_menu)
        self.assertEqual(mod._test_pack,'test')

    def test_focus_rejected_open_does_not_refresh_detached_panel(self):
        Mod=importlib.import_module('story_packs_test.mod').Mod
        mod=Mod();menu=N(panel=N(state='built',menu=None),view=N(closed=False))
        mod.shared=N(menu=None,refresh=Mock())
        mod.native=N(menu=menu,open=Mock(return_value='Waiting for viewport focus'))
        mod._open_conversation_editor=True;mod._return_test_graph=('pack','dialogue')
        mod._open_requested_menu()
        mod.shared.refresh.assert_not_called()
        self.assertFalse(mod._open_conversation_editor)
        self.assertEqual(mod._return_test_graph,('pack','dialogue'))
        self.assertIn('focus',mod.message)

    def test_menu_open_error_does_not_stop_mod_poll(self):
        Mod=importlib.import_module('story_packs_test.mod').Mod
        mod=Mod();mod.poll_fast=lambda:None;mod.want_menu=True
        mod.shared=N(ui_ready=True,menu=None)
        mod.native=N(menu=None,open=Mock(side_effect=RuntimeError('focus lost')))
        mod.poll()
        self.assertFalse(mod.want_menu)
        self.assertIn('focus lost',mod.message)

    def test_pending_presentation_close_does_not_reopen_owned_menu(self):
        Mod=importlib.import_module('story_packs_test.mod').Mod
        mod=Mod();menu=N(panel=N(state='open'))
        mod.shared=N(menu=menu,close_menu=Mock())
        mod.native=N(open=Mock())
        mod._open_requested_menu()
        mod.native.open.assert_not_called()
