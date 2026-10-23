import threading
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33.mods import ModLoader, ModError


class PollAdmissionTests(unittest.TestCase):
    def loader(self, provider='absent'):
        shared=N(console=N(poll=Mock()),poll=Mock(return_value=0),_transport=object(),_closed=False)
        if provider!='absent':shared._poll_readiness=provider
        callback=Mock()
        loader=ModLoader.__new__(ModLoader)
        loader._owner=threading.get_ident();loader._closed=False;loader._polling=False
        loader._session=shared;loader._loaded={'Enabled':[None,N(poll=callback),object()]}
        loader._poll_diagnostics=False;loader._keys=None;loader.registry=Mock()
        return loader,shared,callback

    def test_title_false_and_uncertain_skip_all_native_keys_and_enabled_mods(self):
        for state in (False,None):
            with self.subTest(state=state):
                loader,shared,callback=self.loader(lambda:state)
                with patch('expedition33._session.supports_keys',return_value=True) as supports, \
                     patch('expedition33.keybind_service.KeybindService') as keys:
                    self.assertEqual(loader.poll(),0)
                    shared.console.poll.assert_not_called();shared.poll.assert_not_called()
                    supports.assert_not_called();keys.assert_not_called();callback.assert_not_called()
                    self.assertFalse(loader._polling)

    def test_invalid_provider_and_value_fail_before_native_work(self):
        for provider in (False,lambda:1,lambda:'ready'):
            with self.subTest(provider=provider):
                loader,shared,callback=self.loader(provider)
                with self.assertRaises(ModError):loader.poll()
                shared.console.poll.assert_not_called();shared.poll.assert_not_called();callback.assert_not_called()

    def test_legacy_absent_provider_preserves_native_and_mod_poll(self):
        loader,shared,callback=self.loader()
        with patch('expedition33._session.supports_keys',return_value=False):
            self.assertEqual(loader.poll(),0)
        shared.console.poll.assert_called_once_with();shared.poll.assert_called_once_with();callback.assert_called_once_with()

    def test_first_admission_starts_keys_once_then_normal_polling(self):
        admitted=[False]
        loader,shared,callback=self.loader(lambda:admitted[0])
        key_owner=N(session=shared,poll=Mock(return_value=0))
        with patch('expedition33._session.supports_keys',return_value=True), \
             patch('expedition33.keybind_service.KeybindService',return_value=key_owner) as keys:
            loader.poll();keys.assert_not_called()
            admitted[0]=True
            loader.poll();loader.poll()
            keys.assert_called_once_with(shared,loader.registry)
        self.assertEqual(callback.call_count,2)
        self.assertEqual(shared.poll.call_count,2)
        self.assertEqual(key_owner.poll.call_count,2)

    def test_provider_exception_visible_without_native_work(self):
        failure=RuntimeError('readiness decoder')
        loader,shared,callback=self.loader(Mock(side_effect=failure))
        with self.assertRaises(RuntimeError) as raised:loader.poll()
        self.assertIs(raised.exception,failure)
        shared.poll.assert_not_called();callback.assert_not_called()


if __name__=='__main__':unittest.main()
