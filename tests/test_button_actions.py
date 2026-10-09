import struct
from types import SimpleNamespace
import unittest
from expedition33.menu import NativeMenu, MenuError
from expedition33 import _button_action_wire as wire
from expedition33.sdk import Session

class FakeSession(SimpleNamespace):
    pass

class ButtonActionsTests(unittest.TestCase):
    def setUp(self):
        self.events=[]; self.calls=[]; self.defer=False; self.aborted=False
        self.session=FakeSession(_check=lambda:None, supports_button_actions=True, _menus=set())
        self.session._transport=SimpleNamespace(_check_thread=lambda:None, button_action_session=7,
                                                command=self.command)
        self.session._abort_ownership=self.abort
        self.menu=NativeMenu(self.session,[SimpleNamespace(_token=2),SimpleNamespace(_token=3)])
        self.menu._state='attached'; self.session._menus.add(self.menu)

    def abort(self):
        self.aborted=True
        if self.menu._action: self.menu._action._revoke('unknown')

    def command(self, command, sent=None):
        self.calls.append(command)
        if command=='drain': return {'dropped':0,'events':[]}
        result=bytearray(sent)
        if command=='menu':
            struct.pack_into('<3I',result,8,0,2,0)
            return {'menu_packet':result.hex()}
        operation=wire.HEADER.unpack_from(sent)[1]
        state,registration=(0,0) if operation==3 else (2,12)
        error=913 if operation==3 and self.defer else 0
        if error: state,registration=3,0
        events=self.events if operation==2 else ()
        struct.pack_into('<4I',result,8,error,2,len(events),state)
        struct.pack_into('<Q',result,64,registration)
        for i,event in enumerate(events): wire.EVENT.pack_into(result,72+i*40,*event)
        return {'button_action_packet':result.hex()}

    def event(self, action, sequence=1):
        return (7,12,self.menu._owner,action._action,sequence)

    def test_dispatch_exception_and_replay(self):
        def fail(event): raise SystemExit('mod failed')
        action=self.menu.bind_action(fail)
        self.events=[self.event(action)]
        self.assertEqual(action._poll(),1)
        self.assertIn('SystemExit',action.failures[0])
        with self.assertRaises(MenuError): action._poll()
        self.assertTrue(self.aborted)

    def test_reject_entire_batch_before_delivery(self):
        seen=[]; action=self.menu.bind_action(seen.append)
        bad=list(self.event(action,2)); bad[3]+=1
        self.events=[self.event(action),tuple(bad)]
        with self.assertRaises(MenuError): action._poll()
        self.assertEqual(seen,[])
        self.assertTrue(self.aborted)

    def test_self_remove_discards_remaining_events(self):
        seen=[]
        def callback(event):
            seen.append(event); action.remove()
        action=self.menu.bind_action(callback)
        self.events=[self.event(action),self.event(action,2)]
        self.assertEqual(action._poll(),1)
        self.assertEqual(len(seen),1)
        self.assertFalse(action.active)
        self.menu.bind_action(lambda event:None)

    def test_deferred_remove_and_menu_close(self):
        action=self.menu.bind_action(lambda event:None)
        self.defer=True
        self.assertFalse(action.remove())
        with self.assertRaises(MenuError): self.menu.bind_action(lambda event:None)
        self.defer=False; action._poll()
        self.assertEqual(action._state,'closed')
        second=self.menu.bind_action(lambda event:None)
        self.assertTrue(self.menu.close())
        self.assertEqual(second._state,'closed')
        self.assertEqual(second._poll(),0)

    def test_validation_before_native_binding(self):
        with self.assertRaises(TypeError): self.menu.bind_action(None)
        self.menu._state='prepared'
        with self.assertRaises(MenuError): self.menu.bind_action(lambda event:None)
        self.assertEqual(self.calls,[])

    def test_interrupted_bind_is_not_retryable(self):
        def interrupted(*args): raise KeyboardInterrupt()
        self.session._transport.command=interrupted
        with self.assertRaises(KeyboardInterrupt): self.menu.bind_action(lambda event:None)
        self.assertTrue(self.aborted)
        self.assertEqual(self.menu._action._state,'unknown')
        with self.assertRaises(MenuError): self.menu.bind_action(lambda event:None)

    def test_session_poll_drives_action_delivery(self):
        self.session._polling=False; self.session._closed=False
        self.session._release_pending_leases=lambda:None
        self.session._reconcile=lambda:None
        self.session.dropped_events=0
        self.session._object=SimpleNamespace(pid=1,index=2,serial=3,name='Actor',class_name='Actor')
        seen=[]; action=self.menu.bind_action(seen.append)
        self.events=[self.event(action)]
        self.assertEqual(Session.poll(self.session),1)
        self.assertEqual(len(seen),1)
        self.assertFalse(self.session._polling)


if __name__=='__main__': unittest.main()
