import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.story_media import StoryMediaSource


class MediaMetadataTests(unittest.TestCase):
    def fixture(self,warm=True):
        source=N(index=1,serial=2,address=0x10000,class_name='FileMediaSource')
        function=object();catalog=Mock();catalog.with_observations.return_value=catalog;catalog.find_path.return_value=function
        planner=Mock(_catalog=catalog);planner.prepare.return_value.invoke.return_value=nullcontext()
        metadata=Mock();metadata.planner.return_value=planner
        scope=N(pid=3,_session=N(_file_audio_metadata=metadata if warm else None),invocation_planner=Mock(return_value=planner))
        resources=Mock();resources.load.return_value=source
        return StoryMediaSource(scope,resources),metadata,planner,catalog,source,function
    def value(self,path,*,error=False):return N(values={(1,'FilePath'):path},errors={'path':'unreadable'} if error else {},truncated=False)
    def test_warm_schema_preserves_current_path_and_original_restore(self):
        owner,metadata,planner,catalog,source,function=self.fixture()
        with patch('expedition33.story_media.capture_matching') as scan,patch('expedition33.story_media.capture_selected') as selected,patch('expedition33.story_media.read_values_with_references',side_effect=((self.value('original'),catalog),(self.value('replacement'),catalog),(self.value('original'),catalog))) as read:
            self.assertIs(owner.prepare('/asset','replacement'),owner)
            self.assertTrue(owner.close())
        scan.assert_not_called();selected.assert_not_called();metadata.planner.assert_called_once_with(owner.scope,(source,))
        self.assertEqual([call.kwargs for call in planner.prepare.call_args_list],[dict(Path='replacement'),dict(Path='original')])
        self.assertEqual(read.call_count,3);planner.close.assert_called_once();self.assertEqual(owner.original,'original')
    def test_unreadable_original_path_closes_only_planner_without_mutation(self):
        owner,metadata,planner,catalog,source,function=self.fixture()
        with patch('expedition33.story_media.read_values_with_references',return_value=(self.value('bad',error=True),catalog)):
            with self.assertRaisesRegex(RuntimeError,'observation incomplete'):owner.prepare('/asset','replacement')
        planner.prepare.assert_not_called();planner.close.assert_called_once();self.assertIsNone(owner.planner)
    def test_changed_metadata_does_not_fall_back_to_global_discovery(self):
        owner,metadata,planner,catalog,source,function=self.fixture();metadata.planner.side_effect=RuntimeError('metadata scope closed')
        with patch('expedition33.story_media.capture_matching') as scan:
            with self.assertRaisesRegex(RuntimeError,'scope closed'):owner.prepare('/asset','replacement')
        scan.assert_not_called();planner.prepare.assert_not_called()
    def test_unknown_mutation_is_retained_and_never_replayed(self):
        owner,metadata,planner,catalog,source,function=self.fixture();planner.prepare.return_value.invoke.side_effect=RuntimeError('unknown native result')
        with patch('expedition33.story_media.read_values_with_references',return_value=(self.value('original'),catalog)):
            with self.assertRaisesRegex(RuntimeError,'unknown native'):owner.prepare('/asset','replacement')
        self.assertFalse(owner.close());planner.prepare.return_value.invoke.assert_called_once()
        with self.assertRaisesRegex(RuntimeError,'already prepared'):owner.prepare('/asset','replacement')
    def test_generic_sdk_without_warmed_audio_keeps_original_discovery_path(self):
        owner,metadata,planner,catalog,source,function=self.fixture(warm=False)
        with patch('expedition33.story_media.capture_matching',return_value=catalog) as scan,patch('expedition33.story_media.capture_selected',return_value=catalog),patch('expedition33.story_media.read_values_with_references',side_effect=((self.value('original'),catalog),(self.value('replacement'),catalog))):
            owner.prepare('/asset','replacement')
        scan.assert_called_once_with(3,names=('SetFilePath',));metadata.planner.assert_not_called()
        owner.scope.invocation_planner.assert_called_once_with(catalog=catalog,selected_results=True)


if __name__=='__main__':unittest.main()
