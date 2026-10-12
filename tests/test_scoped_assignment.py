import unittest
from types import SimpleNamespace
from expedition33._scoped_assignment import HEADER, SIZE, NativeScopedAssignment, validate_request


class ScopedAssignmentTests(unittest.TestCase):
    def test_rejects_payload_on_close(self):
        data = HEADER.pack(1, 2, 5, 0, 0, 0) + bytes(SIZE-HEADER.size)
        validate_request(data)
        with self.assertRaises(ValueError):
            validate_request(data[:-1] + b'\1')

    def session(self, reply):
        session = SimpleNamespace(_check=lambda: None, aborted=False)
        session._abort_ownership = lambda: setattr(session, 'aborted', True)
        session._transport = SimpleNamespace(command=lambda name, data: {'scoped_assignment_packet': reply(data).hex()})
        return session

    def test_changed_acknowledgement_aborts(self):
        session = self.session(lambda data: data[:-1]+b'\1')
        owner = NativeScopedAssignment(SimpleNamespace(_session=session, _reference_owners=[]))
        owner.state = 'armed'
        with self.assertRaises(ValueError): owner.close()
        self.assertTrue(session.aborted)
        self.assertEqual(owner.state, 'unknown')

    def test_confirmed_close_is_idempotent(self):
        session = self.session(lambda data: data)
        owner = NativeScopedAssignment(SimpleNamespace(_session=session, _reference_owners=[]))
        owner.state = 'armed'
        self.assertTrue(owner.close())
        self.assertTrue(owner.close())
        self.assertFalse(session.aborted)

    def test_pre_dispatch_deferral_keeps_owner(self):
        session = self.session(lambda data: data[:24] + HEADER.pack(1,1,1,0,407,1)[24:] + data[32:])
        owner = NativeScopedAssignment(SimpleNamespace(_session=session, _reference_owners=[]))
        owner.state = 'armed'
        self.assertFalse(owner.close())
        self.assertEqual(owner.state, 'armed')
        self.assertFalse(session.aborted)
