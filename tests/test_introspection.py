"""Original core provenance and adapted request lifecycle, separate from live proof."""
import hashlib
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from expedition33.introspection import Harness, UnsupportedCapability, core


class IntrospectionTests(unittest.TestCase):
    def test_original_core_preserved(self):
        self.assertEqual(hashlib.sha256(Path(core.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            '6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543')

    def test_capabilities_do_not_claim_parity(self):
        with Harness() as h:
            status = h.request({'op': 'status'})
            self.assertFalse(status['parity_complete'])
            self.assertIn('invoke', status['original_operations'])
            self.assertNotIn('invoke', status['operations'])
            with self.assertRaises(UnsupportedCapability): h.request({'op': 'invoke'})
        with self.assertRaises(RuntimeError): h.request({'op': 'status'})

    def test_request_failure_releases_catalog_and_recovers(self):
        with Harness() as h:
            with patch('expedition33.introspection.capture', side_effect=ValueError('broken observation')):
                with self.assertRaises(ValueError):
                    h.request({'op': 'search', 'offset': 'bad'})
            self.assertIsNone(h._backend.catalog)
            self.assertEqual(h.request({'op': 'status'})['retained_values'], [])

    def test_thread_ownership(self):
        with Harness() as h:
            errors = []
            def worker():
                try: h.request({'op': 'status'})
                except RuntimeError as exc: errors.append(str(exc))
            thread = threading.Thread(target=worker); thread.start(); thread.join()
            self.assertEqual(len(errors), 1)


if __name__ == '__main__': unittest.main()
