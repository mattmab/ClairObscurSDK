import io,json,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import RuntimeQueryError
from expedition33._asset_names import resolve
from expedition33._reader import ReadBatch,_active

PATH='/Game/Test.Test'
def response(**changes):
    row=dict(event='asset_names',package='/Game/Test',asset='Test',package_id=123,asset_id=456);row.update(changes)
    return '\n'.join(json.dumps(r) for r in (dict(event='snapshot_start',pid=17),row,dict(event='snapshot_end',emitted=1)))


class AssetNameReaderTests(unittest.TestCase):
    def scope(self):return N(pid=17,_session=N(_transport=N(_executable='reader.exe')))
    def test_qualified_active_reader_is_used_without_subprocess_or_cached_result(self):
        reader=N(pid=17,supports_asset_names=True,query=Mock(return_value=response()),close=Mock())
        with patch('expedition33._asset_names.active_reader',return_value=reader),\
             patch('expedition33._asset_names.subprocess.run',side_effect=AssertionError('no new probe')):
            self.assertEqual(resolve(self.scope(),PATH)['package_id'],123)
            resolve(self.scope(),PATH,export=True)
        self.assertEqual(reader.query.call_args_list[0].args[0],['--resolve-asset-names','17',PATH])
        self.assertEqual(reader.query.call_args_list[1].args[0],['--resolve-export-names','17',PATH])
        reader.close.assert_not_called()
    def test_old_worker_uses_existing_probe_but_failed_qualified_worker_never_falls_back(self):
        reader=N(pid=17,supports_asset_names=False)
        with patch('expedition33._asset_names.active_reader',return_value=reader),\
             patch('expedition33._asset_names.subprocess.run',return_value=N(returncode=0,stdout=response())) as run:
            resolve(self.scope(),PATH)
        run.assert_called_once()
        reader=N(pid=17,supports_asset_names=True,query=Mock(side_effect=RuntimeQueryError('terminal')),close=Mock())
        with patch('expedition33._asset_names.active_reader',return_value=reader),\
             patch('expedition33._asset_names.subprocess.run',side_effect=AssertionError('no fallback')):
            with self.assertRaisesRegex(RuntimeQueryError,'terminal'):resolve(self.scope(),PATH)
    def test_malformed_name_receipts_close_worker_before_exposing_ids(self):
        bad=[response(package_id=True),response(asset_id=0),response(asset_id=0x20000000),response(asset='Other'),
             '[]',response().replace('"pid": 17','"pid": 18'),response().replace('"emitted": 1','"emitted": true')]
        for output in bad:
            reader=N(pid=17,supports_asset_names=True,query=Mock(return_value=output),close=Mock())
            with patch('expedition33._asset_names.active_reader',return_value=reader):
                with self.assertRaises((ValueError,TypeError)):resolve(self.scope(),PATH)
            reader.close.assert_called_once()
    def test_numbered_name_receipt_must_reconstruct_the_requested_suffix(self):
        path='/Game/Test_2.Test_2'
        output=response(package='/Game/Test_2',asset='Test_2',package_number=3,asset_number=3)
        reader=N(pid=17,supports_asset_names=True,query=Mock(return_value=output),close=Mock())
        with patch('expedition33._asset_names.active_reader',return_value=reader):
            self.assertEqual(resolve(self.scope(),path)['asset_number'],3)
        for changes in (dict(asset_number=True),dict(asset_number=0x80000000),dict(asset_number=2),dict(package_number=-1)):
            reader.query.return_value=response(package='/Game/Test_2',asset='Test_2',package_number=3,**changes) if 'package_number' not in changes else response(package='/Game/Test_2',asset='Test_2',asset_number=3,**changes)
            with patch('expedition33._asset_names.active_reader',return_value=reader):
                with self.assertRaises(ValueError):resolve(self.scope(),path)
    def test_reader_gate_requires_negotiated_capability_and_pinned_pid(self):
        reader=ReadBatch(17);reader._process=N(stdin=io.StringIO());reader._token=_active.set(reader)
        try:
            with self.assertRaises(RuntimeQueryError):reader.query(['--resolve-asset-names','17',PATH])
            reader.supports_asset_names=True
            with self.assertRaises(RuntimeQueryError):reader.query(['--resolve-asset-names','18',PATH])
            with self.assertRaises(RuntimeQueryError):reader.query(['--resolve-asset-names','17',PATH+'\n--session'])
            self.assertEqual(reader._process.stdin.getvalue(),'')
        finally:_active.reset(reader._token);reader._token=None;reader._process=None
