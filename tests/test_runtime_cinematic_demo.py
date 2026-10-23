"""Fail-closed controller/acknowledgement tests; not evidence of engine playback."""
import importlib.util
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runtime_cinematic_demo_test',ROOT/'mods/RuntimeCinematicDemo/mod.py')
demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)


class Transport:
    runtime_cinematic_protocol=2
    def __init__(self,mutate=None):self.calls=[];self.mutate=mutate
    def command(self,name,packet):
        self.calls.append((name,packet))
        raw=bytearray(packet)
        if self.mutate:self.mutate(raw)
        return {'mesh_packet':bytes(raw).hex()}


class CinematicDemoTests(unittest.TestCase):
    def model(self,transport):
        mod=demo.Mod();mod.session=SimpleNamespace(_session=SimpleNamespace(_transport=transport))
        return mod

    def test_missing_native_capability_cannot_allocate_or_dispatch(self):
        transport=Transport();transport.runtime_cinematic_protocol=0
        mod=self.model(transport)
        with self.assertRaisesRegex(RuntimeError,'isolated'):mod.start()
        self.assertIsNone(mod.scope);self.assertEqual(transport.calls,[])

    def test_stale_echo_quarantines_and_never_resends(self):
        transport=Transport(lambda raw:raw.__setitem__(16,raw[16]^1))
        mod=self.model(transport)
        with self.assertRaisesRegex(RuntimeError,'mismatch'):mod._command(73)
        with self.assertRaisesRegex(RuntimeError,'Unknown native outcome'):mod._command(72)
        self.assertEqual(len(transport.calls),1)

    def test_rejects_tampering_with_any_input_identity(self):
        transport=Transport(lambda raw:raw.__setitem__(100,1))
        mod=self.model(transport)
        with self.assertRaisesRegex(RuntimeError,'mismatch'):mod._command(73)
        self.assertTrue(mod.uncertain)

    def test_native_rejection_is_not_mistaken_for_success(self):
        transport=Transport(lambda raw:struct.pack_into('<I',raw,8,2004))
        mod=self.model(transport)
        with self.assertRaisesRegex(RuntimeError,'2004'):mod._command(73)
        self.assertFalse(mod.last['live_success']);self.assertFalse(mod.uncertain)

    def test_deferred_cleanup_retains_ownership(self):
        def deferred(raw):
            struct.pack_into('<II',raw,8,407,3);struct.pack_into('<I',raw,20976,5)
        mod=self.model(Transport(deferred))
        result=mod._command(72)
        self.assertEqual(result['state'],'cleanup_pending');self.assertEqual(result['private_leases'],5)

    def test_prepare_cannot_send_an_incomplete_identity_set(self):
        transport=Transport();mod=self.model(transport)
        with self.assertRaisesRegex(ValueError,'input count'):mod._command(70,())
        self.assertEqual(transport.calls,[])


if __name__=='__main__':unittest.main()
