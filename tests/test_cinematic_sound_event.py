import unittest
from types import SimpleNamespace

from expedition33._cinematic_sound_event import HEADER, SIZE, NativeCinematicSoundEvent, validate_request


class CinematicSoundEventTests(unittest.TestCase):
    def owner(self, transform):
        session = SimpleNamespace(_check=lambda: None, aborted=False)
        session._abort_ownership = lambda: setattr(session, 'aborted', True)
        session._transport = SimpleNamespace(command=lambda name, data: {
            'cinematic_sound_event_packet': transform(data).hex()})
        owner = NativeCinematicSoundEvent(SimpleNamespace(_session=session, _audio_owners=[]))
        owner.state = 'armed'
        return owner, session

    @staticmethod
    def reply(data, error=0, state=0, observed=0, failed=0):
        return data[:24] + HEADER.pack(1, 1, 1, 0, error, state, observed, failed)[24:] + data[40:]

    def test_status_does_not_accept_payload(self):
        request = HEADER.pack(1, 3, 42, 0, 0, 0, 0, 0) + bytes(SIZE-40)
        validate_request(request)
        with self.assertRaises(ValueError):
            validate_request(request[:-1] + b'\1')

    def test_cleanup_defers_without_releasing_owner(self):
        owner, session = self.owner(lambda data: self.reply(data, error=407, state=1))
        self.assertFalse(owner.close())
        self.assertEqual(owner.state, 'armed')
        self.assertFalse(session.aborted)

    def test_uncertain_dispatch_aborts_without_retry(self):
        owner, session = self.owner(lambda data: self.reply(data, state=2, observed=1, failed=1))
        with self.assertRaises(RuntimeError):
            owner.status()
        self.assertTrue(session.aborted)
        with self.assertRaises(RuntimeError):
            owner.close()

    def test_ack_cannot_change_owned_function(self):
        owner, session = self.owner(lambda data: data[:40] + b'\1' + data[41:])
        with self.assertRaises(ValueError):
            owner.close()
        self.assertTrue(session.aborted)

    def test_cleanup_preserves_event_counts(self):
        owner, session = self.owner(lambda data: self.reply(data, observed=2))
        self.assertTrue(owner.close())
        self.assertEqual((owner.state, owner.observed, owner.failed), ('closed', 2, 0))
        self.assertFalse(session.aborted)
