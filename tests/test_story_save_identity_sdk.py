import struct
import unittest
from contextlib import nullcontext
from unittest.mock import Mock
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33._story_identity_wire import encode
from expedition33.story_save_identity import decode,IdentityError,StorySaveIdentity


class StoryIdentitySdkTests(unittest.TestCase):
    def test_loading_discovery_failure_dispatches_nothing_and_keeps_identity_owner_retryable(self):
        from expedition33 import RuntimeQueryError
        from expedition33.story_save_identity import observe,StoryIdentityNotReady
        transport=N(command=Mock())
        owner=StorySaveIdentity.__new__(StorySaveIdentity)
        owner.closed=False;owner.unknown=False;owner.scope=N(pid=123,_session=N(_transport=transport));owner.observer=observe
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),patch('expedition33.story_save_identity._observe',side_effect=RuntimeQueryError('Catalog outer missing or changed; refresh required')):
            with self.assertRaises(StoryIdentityNotReady):owner.read()
        self.assertFalse(owner.unknown);transport.command.assert_not_called()
    def test_unrecognized_discovery_failure_is_not_relabelled_loading(self):
        from expedition33 import RuntimeQueryError
        from expedition33.story_save_identity import observe,StoryIdentityNotReady
        with patch('expedition33._reader.shared_operation',return_value=nullcontext()),patch('expedition33.story_save_identity._observe',side_effect=RuntimeQueryError('Unexpected schema')):
            with self.assertRaises(RuntimeQueryError) as caught:observe(N(pid=123))
        self.assertNotIsInstance(caught.exception,StoryIdentityNotReady)
    def request(self,insert=False):
        return encode(1,2,[N(index=i,serial=i+1,address=0x10000+i*16) for i in range(6)],
            'e33c5701'+'0'*24,insert=insert)

    def test_read_returns_copied_save_identity_and_absence_is_explicit(self):
        sent=self.request();reply=bytearray(sent);struct.pack_into('<I',reply,12,1)
        struct.pack_into('<4I',reply,128,0xe33c5701,3,4,5)
        self.assertEqual(decode(sent,bytes(reply)),'e33c5701000000030000000400000005')
        reply=bytearray(sent);struct.pack_into('<I',reply,12,2)
        self.assertIsNone(decode(sent,bytes(reply)))

    def test_bind_cannot_acknowledge_different_identity_or_absence(self):
        sent=self.request(True)
        for state in (1,2):
            reply=bytearray(sent);struct.pack_into('<I',reply,12,state)
            struct.pack_into('<I',reply,132,7)
            with self.assertRaises(RuntimeError):decode(sent,bytes(reply))

    def test_read_cannot_change_context_or_return_identity_on_rejection(self):
        sent=self.request()
        for at in (0,4,24,120,128,144,152):
            reply=bytearray(sent);struct.pack_into('<I',reply,12,1);reply[at]^=1
            with self.assertRaises(RuntimeError):decode(sent,bytes(reply))
        reply=bytearray(sent);struct.pack_into('<I',reply,8,3881)
        with self.assertRaises(IdentityError) as caught:decode(sent,bytes(reply))
        self.assertEqual(caught.exception.code,3881)

    def test_older_identity_writer_is_not_a_reader(self):
        for cap in (0,1,True,3):
            scope=N(_check=lambda:None,_session=N(_transport=N(story_save_identity_protocol=cap)))
            with patch('expedition33._scope.SessionScope') as child:
                with self.assertRaises(RuntimeError):StorySaveIdentity(scope)
                child.assert_not_called()
