import struct
from types import SimpleNamespace
import unittest
from expedition33 import _multi_button_wire as wire
from expedition33.menu import NativeMenu, MenuError


class Lease:
    def __init__(self, token):
        self._token = token; self.active = True
        self.object = SimpleNamespace(pid=1, index=token, serial=1, address=0x10000 + token*8)


class FakeSession(SimpleNamespace):
    pass


class MultiControlsTests(unittest.TestCase):
    def setUp(self):
        self.leases = [Lease(i) for i in range(1, 5)]
        self.session = FakeSession(_check=lambda: None, supports_multi_controls=True,
                                       _leases=set(self.leases), _menus=set())
        self.session._transport = SimpleNamespace(_check_thread=lambda: None,
                                                  button_action_session=7, command=self.command)
        self.session._abort_ownership = self.abort
        self.menu = NativeMenu(self.session, self.leases[:2])
        self.menu._state = 'attached'; self.session._menus.add(self.menu)
        self.events = []; self.registrations = {}; self.next = 0
        self.aborted = False; self.defer = False; self.sent = []

    def abort(self):
        self.aborted = True
        if self.menu._controls: self.menu._controls.revoke('unknown')

    def command(self, name, sent):
        self.sent.append(name)
        result = bytearray(sent)
        if name == 'menu':
            struct.pack_into('<3I', result, 8, 0, 2, 0)
            return {'menu_packet': result.hex()}
        op = wire.HEADER.unpack_from(sent)[1]
        lease = struct.unpack_from('<Q', sent, 40)[0]
        error = 1013 if self.defer and op == 3 else 0
        if op == 1:
            self.next += 1; self.registrations[lease] = self.next
        if op == 3 and not error: self.registrations.pop(lease)
        registration = self.registrations.get(lease, 0) if not error else 0
        events = self.events if op == 2 else []
        struct.pack_into('<4I', result, 8, error, 2, len(events), 3 if error else 2 if registration else 0)
        struct.pack_into('<Q', result, 64, registration)
        for i, event in enumerate(events): wire.EVENT.pack_into(result, 72+i*40, *event)
        if op == 2: self.events = []
        return {'multi_button_packet': result.hex()}

    def bind(self, index, callback): return self.menu.bind_control(self.leases[index].object, callback)
    def event(self, control, sequence):
        return (7, control._registration, self.menu._owner, control._action, sequence)

    def test_two_controls_one_drain_and_protected_leases(self):
        seen = []; a = self.bind(2, lambda e: seen.append('a')); b = self.bind(3, lambda e: seen.append('b'))
        self.assertTrue(self.menu.protects(self.leases[2]))
        self.events = [self.event(a, 1), self.event(b, 2)]
        before = len(self.sent)
        self.assertEqual(self.menu._controls.poll(), 2)
        self.assertEqual(len(self.sent)-before, 1)
        self.assertEqual(seen, ['a', 'b'])
        self.assertTrue(a.remove()); self.assertFalse(self.menu.protects(self.leases[2]))
        self.assertTrue(self.menu.protects(self.leases[3]))

    def test_validate_whole_batch_before_callbacks(self):
        seen = []; a = self.bind(2, seen.append)
        self.events = [self.event(a, 1), (7, 999, self.menu._owner, 8, 2)]
        with self.assertRaises(MenuError): self.menu._controls.poll()
        self.assertEqual(seen, []); self.assertTrue(self.aborted)
        self.assertTrue(self.menu.protects(self.leases[2]))

    def test_callback_removes_other_control_from_drained_batch(self):
        seen = []
        a = self.bind(2, lambda e: b.remove())
        b = self.bind(3, seen.append)
        self.events = [self.event(a, 1), self.event(b, 2)]
        self.assertEqual(self.menu._controls.poll(), 1)
        self.assertEqual(seen, [])

    def test_callback_closes_menu_and_contains_exception(self):
        def close(event):
            self.menu.close()
            raise RuntimeError('contained')
        a = self.bind(2, close); b = self.bind(3, lambda e: self.fail('revoked callback'))
        self.events = [self.event(a, 1), self.event(b, 2)]
        self.assertEqual(self.menu._controls.poll(), 1)
        self.assertIn('contained', a.failures[0]); self.assertFalse(b.active)
        self.assertFalse(self.menu.protects(self.leases[2]))

    def test_deferred_remove_revokes_callback_but_protects_lease(self):
        a = self.bind(2, lambda e: self.fail('revoked'))
        self.defer = True
        self.assertFalse(a.remove()); self.assertFalse(a.active)
        self.assertTrue(self.menu.protects(self.leases[2]))
        self.defer = False
        self.assertEqual(self.menu._controls.poll(), 0)
        self.assertFalse(self.menu.protects(self.leases[2]))

    def test_duplicate_and_unowned_controls_rejected_before_send(self):
        self.bind(2, lambda e: None)
        before = len(self.sent)
        with self.assertRaises(MenuError): self.bind(2, lambda e: None)
        with self.assertRaises(ValueError): self.menu.bind_control(Lease(99).object, lambda e: None)
        self.assertEqual(before, len(self.sent))

    def test_single_control_does_not_ignore_an_unresolved_alias(self):
        self.session.pid=1
        pending=Lease(99);target=self.leases[2].object
        pending._pending_identity=(target.pid,target.index,target.serial,target.address);pending.object=None
        self.session._leases.add(pending)
        with self.assertRaises(ValueError):self.bind(2,lambda e:None)
        self.assertEqual(self.sent,[]);self.assertTrue(pending.active)
        pending._pending_identity=(1,99,1,0x10318)
        action=self.bind(2,lambda e:None)
        self.assertTrue(action.active);self.assertIn(pending,self.session._leases)
