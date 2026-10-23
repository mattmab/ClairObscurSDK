import importlib.util
from pathlib import Path
import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock
from test_cinematics import module as browser
from expedition33.cinematics import presentation

from expedition33 import management_native as management
from expedition33._menu_latency import MenuLatency

class DeferredPresentationTests(unittest.TestCase):
    def setUp(self):
        self.events=[];self.callbacks=[]
        self.native=N(bind_controls=self.bind,remove_controls=lambda actions:self.events.append('unbind') or True)
        self.panel=N(state='open',uncertain=False,menu=self.native,buttons=list(range(12)),
            paint_batch=nullcontext,_mutate=lambda fn,*args:fn(*args))
        self.menu=management.NativeManagementMenu.__new__(management.NativeManagementMenu)
        self.menu.latency=MenuLatency()
        self.menu._button_colors={}
        self.menu.panel=self.panel;self.menu.actions=[];self.menu.failure=None
        self.menu._accept_input=True;self.menu._presentation_suspended=False;self.menu._presentation_dirty=False
        self.menu._reusable=True;self.menu.error=None
        self.menu._paint_frame=lambda:self.events.append('paint')
        self.guard=presentation.MenuPresentation(self.menu)
        self.guard.state='prepared';self.guard.planner=N(close=lambda:self.events.append('planner_close'))
        self.guard.hide_call=N(invoke=lambda:self.events.append('hide') or nullcontext())
        self.guard.restore_call=N(invoke=lambda:self.events.append('show') or nullcontext())
        scene=dict(id=browser.DEFINITION,title='Prologue',reason='ready',supported=True,unlocked=True,replay_kind='title')
        self.model=N(show_all=False,discovery={'confirmed':[scene]},reason='',playback_status='Starting',
            control=Mock(side_effect=lambda *args:self.guard.suspend()))
        self.menu.view=browser.BrowserView(N(_check=Mock()),self.model)
        self.menu.view.selected=browser.DEFINITION
        self.menu.frame=self.menu.view.render()
        self.menu._bind()
        self.play_callback=self.callbacks[2][1]
        self.events.clear()

    def bind(self, bindings):
        self.events.append('bind')
        self.callbacks=list(bindings)
        return [object() for _ in bindings]

    def test_real_browser_play_callback_defers_paint_and_rebind_until_restore(self):
        old_actions=list(self.menu.actions)
        self.play_callback(None)
        self.model.control.assert_called_once_with(browser.DEFINITION,1)
        self.assertEqual(self.events,['hide'])
        self.assertEqual(self.menu.actions,old_actions)
        self.assertTrue(self.menu._presentation_dirty)
        old_revision=self.menu.frame.revision
        self.menu.refresh()
        self.assertGreater(self.menu.frame.revision,old_revision)
        self.assertEqual(self.events,['hide'])
        self.play_callback(None) # Existing registrations are gated during suspension.
        self.assertEqual(self.model.control.call_count,1)
        self.guard.restore()
        self.assertEqual(self.events,['hide','unbind','paint','bind','show','planner_close'])
        self.assertFalse(self.menu._presentation_suspended)
        self.assertFalse(self.menu._presentation_dirty)
        self.assertEqual(self.guard.state,'restored')
        self.guard.restore()
        self.assertEqual(self.events.count('paint'),1)

    def test_deferred_frame_failure_keeps_presentation_gated_and_never_retries(self):
        self.play_callback(None)
        self.menu._paint_frame=Mock(side_effect=RuntimeError('paint uncertain'))
        with self.assertRaisesRegex(RuntimeError,'paint uncertain'):self.guard.restore()
        self.assertTrue(self.menu._presentation_suspended)
        self.assertIs(self.menu._presentation_owner,self.guard)
        self.assertNotIn('show',self.events)
        with self.assertRaisesRegex(Exception,'refresh failed'):self.guard.restore()
        self.menu._paint_frame.assert_called_once()

    def test_direct_paint_is_deferred_while_suspended(self):
        self.play_callback(None)
        self.menu._paint()
        self.assertEqual(self.events,['hide'])

if __name__=='__main__':unittest.main()

