import io
import hashlib
from unittest.mock import patch
from pathlib import Path
import tempfile
import unittest
import zipfile
import package_rc18 as release

class RC18PackagingTests(unittest.TestCase):
    def setUp(self):
        # Synthetic fixtures only: no actual local identifier belongs in tests.
        self.private_tokens=(b'fixtureprivateonly',b'0123456789abcdef0123456789abcdef')
        rules=(('word',len(self.private_tokens[0]),hashlib.sha256(self.private_tokens[0]).hexdigest()),
               ('hex',32,hashlib.sha256(self.private_tokens[1]).hexdigest()))
        guard=patch.object(release,'PRIVATE_FINGERPRINTS',rules)
        guard.start();self.addCleanup(guard.stop)

    def archive(self,entries):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as archive:
            for name,value in entries.items():archive.writestr(name,value)
        return data.getvalue()
    def audit_bytes(self,data):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'fixture.zip';path.write_bytes(data)
            return release.audit(path)
    def test_fingerprint_guard_detects_embedded_tokens_without_exposing_them(self):
        self.assertTrue(release.contains_private_identifier(b'prefix'+self.private_tokens[0]+b'suffix'))
        self.assertTrue(release.contains_private_identifier(b'prefix'+self.private_tokens[1]+b'suffix'))
        self.assertFalse(release.contains_private_identifier(b'public SDK source'))
        for kind,length,digest in release.PRIVATE_FINGERPRINTS:
            self.assertIn(kind,('word','hex'));self.assertIn(length,(18,32))
            self.assertEqual(len(digest),64)

    def test_public_inventory_uses_new_loader_and_complete_native_source(self):
        self.assertIn('WorldBuilderMapLoader',release.OPTIONAL)
        self.assertNotIn('E33MapOverlays',release.OPTIONAL)
        names=release.REQUIRED_SOURCES|{'gpu/bridge_test.cpp','mods/E33MapOverlays/mod.py','mods/UnknownLocal/mod.py','settings/management.json','AGENTS.md','README.md'}
        selected=release.source_inventory(names)
        self.assertIn('mods/WorldBuilderMapLoader/context_observer.py',selected)
        self.assertIn('src/expedition33/_stable_lease.py',selected);self.assertIn('gpu/bridge_test.cpp',selected)
        self.assertNotIn('mods/E33MapOverlays/mod.py',selected);self.assertNotIn('mods/UnknownLocal/mod.py',selected)
        self.assertNotIn('settings/management.json',selected);self.assertNotIn('AGENTS.md',selected)
    def test_local_research_scripts_are_excluded_but_core_build_inputs_remain(self):
        names=release.REQUIRED_SOURCES|set(release.SOURCE_EXCLUDES)
        selected=release.source_inventory(names)
        self.assertEqual(len(release.SOURCE_EXCLUDES),11)
        self.assertTrue(all(reason for reason in release.SOURCE_EXCLUDES.values()))
        self.assertTrue(set(selected).isdisjoint(release.SOURCE_EXCLUDES))
        for name in ('scripts/build-rc18-native.cmd','scripts/build-early-lifecycle-runtime.cmd',
                     'scripts/build-bootstrap.cmd','scripts/prepare_runtime.py',
                     'scripts/run_release_sdk.py','scripts/package_release_candidate.py'):
            self.assertIn(name,selected)

    def test_required_new_sources_cannot_be_omitted_from_tracked_inventory(self):
        missing='mods/WorldBuilderMapLoader/context_observer.py'
        with self.assertRaisesRegex(ValueError,'Required public source inputs'):
            release.source_inventory(release.REQUIRED_SOURCES-{missing})
    def test_recursive_nested_mod_audit_rejects_local_state_content_and_legacy_loader(self):
        for entries in ({'settings/prefs.json':b'{}'},{'mod.py':self.private_tokens[0]}, {'saved.e33map.json':b'{}'}):
            nested=self.archive(entries)
            with self.assertRaises(ValueError):self.audit_bytes(self.archive({'SDK_Mods/Public.sdkmod':nested}))
        with self.assertRaises(ValueError):self.audit_bytes(self.archive({'SDK_Mods/E33MapOverlays.sdkmod':self.archive({'mod.py':b'pass'})}))
    def test_nested_local_audit_and_qa_source_are_never_release_inputs(self):
        for name in ('SDK-capability-review/trace.json','SDK/mods/QABattleExplorer/mod.py',
                     'SDK_Mods/QABattleExplorer.sdkmod'):
            with self.assertRaises(ValueError):
                self.audit_bytes(self.archive({'outer.zip':self.archive({name:b'local'})}))
        self.assertNotIn('QABattleExplorer',release.PUBLIC_SOURCE_MODS)

    def test_nested_private_utf16_tokens_are_rejected(self):
        for token in self.private_tokens:
            for encoding in ('utf-16le','utf-16be'):
                data=token.decode('ascii').upper().encode(encoding)
                nested=self.archive({'module.py':data})
                with self.assertRaises(ValueError):
                    self.audit_bytes(self.archive({'SDK_Mods/Public.sdkmod':nested}))

    def test_runtime_bytecode_exception_is_exact_and_privacy_still_applies(self):
        runtime=self.archive({'module.pyc':b'bytecode'})
        self.assertEqual(self.audit_bytes(self.archive({'SDK/runtime/python313.zip':runtime})),2)
        with self.assertRaises(ValueError):self.audit_bytes(self.archive({'unreviewed.zip':runtime}))
        bad=self.archive({'module.pyc':self.private_tokens[1]})
        with self.assertRaises(ValueError):self.audit_bytes(self.archive({'SDK/runtime/python313.zip':bad}))
    def test_corrupt_nested_zip_and_unsafe_paths_fail_closed(self):
        with self.assertRaises(zipfile.BadZipFile):self.audit_bytes(self.archive({'SDK_Mods/Public.sdkmod':b'not an archive'}))
        for name in ('../outside','/absolute','C:/outside','SDK/logs/log.txt'):
            with self.assertRaises(ValueError):release.validate_entry(name,b'public')
