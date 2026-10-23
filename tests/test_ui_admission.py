from contextlib import nullcontext
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch
from expedition33 import RuntimeQueryError
from expedition33.world_admission import Admission

SOURCE=Path(__file__).resolve().parents[1]/'src/expedition33/ui_admission.py'
spec=importlib.util.spec_from_file_location('expedition33._ui_admission_candidate',SOURCE)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)


class UiProbeTests(unittest.TestCase):
    def test_warm_binding_uses_fast_fresh_gate_then_rediscovers_after_invalidation(self):
        observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        observer._activation_binding=('selected',)
        def fast():
            observer._activation_binding=None
            return Admission('observation_pending','activation_reference_changed')
        with patch.object(m.WarmAdmissionObserver,'observe_activation',side_effect=fast) as selected, \
             patch.object(m.WarmAdmissionObserver,'observe',return_value=Admission('inactive','test')) as full, \
             patch.object(m,'capture_selected') as pause:
            self.assertEqual(observer.observe().admission.reason,'activation_reference_changed')
            full.assert_not_called();selected.assert_called_once();pause.assert_not_called()
            self.assertEqual(observer.observe().admission.state,'inactive')
            full.assert_called_once();self.assertEqual(selected.call_count,1)
    def test_selected_current_controller_projection_without_registry_search(self):
        world=N(pid=7,index=3,serial=1,address=0x10300,class_name='World')
        controller=N(index=4)
        catalog=N(by_index={4:controller,9:object()},outer_chain=lambda target:(world,))
        result=Admission('world_ready','test',((7,3,1,0x10300),(7,5,1,0x10500),'manager',0),True)
        observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        observer.pid=7;observer._reader=N(bind=lambda:nullcontext());observer._ui_controller=(7,4,1,0x10400);observer._ui_local_player=(7,6,1,0x10600)
        with patch.object(m.WarmAdmissionObserver,'observe',return_value=result), \
             patch.object(m,'capture_selected',return_value=catalog) as select, \
             patch.object(m,'read_values_many',return_value={4:N(types={(9,'PauseMenuWidget'):'ObjectProperty'})}) as values, \
             patch.object(m,'read_object_reference',return_value=(N(class_name='WBP_PauseMenu_C'),catalog)) as reference:
            self.assertTrue(observer.observe().menu_ready)
            select.assert_called_once_with(7,((4,1,0x10400),))
            values.assert_called_once_with(catalog,(controller,),fields=('PauseMenuWidget',))
            self.assertEqual(reference.call_args.kwargs,{'project':True})

    def test_inactive_and_uncertain_skip_ui_queries(self):
        observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        for state,expected in (('inactive',False),('loading',False),('observation_pending',None)):
            with patch.object(m.WarmAdmissionObserver,'observe',return_value=Admission(state,'test')), \
                 patch.object(m,'capture_selected') as select:
                self.assertIs(observer.observe().menu_ready,expected);select.assert_not_called()

    def test_ui_read_race_is_uncertain_and_discards_worker_without_retry(self):
        observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        observer.pid=7;observer._reader=N(bind=lambda:nullcontext());observer._ui_controller=(7,4,1,0x10400);observer._ui_local_player=(7,6,1,0x10600)
        observer._discard=Mock()
        with patch.object(m.WarmAdmissionObserver,'observe',return_value=Admission('world_ready','test',('epoch',),True)), \
             patch.object(m,'capture_selected',side_effect=RuntimeQueryError('READ_FAILED')) as select:
            self.assertIsNone(observer.observe().menu_ready)
            observer._discard.assert_called_once_with();self.assertEqual(select.call_count,1)

    def test_controller_world_change_inhibits_ui_without_querying_pause(self):
        observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        observer.pid=7;observer._reader=N(bind=lambda:nullcontext());observer._ui_controller=(7,4,1,0x10400);observer._ui_local_player=(7,6,1,0x10600)
        catalog=N(by_index={4:object()},outer_chain=lambda target:())
        with patch.object(m.WarmAdmissionObserver,'observe',return_value=Admission('world_ready','test',('epoch',),True)), \
             patch.object(m,'capture_selected',return_value=catalog), \
             patch.object(m,'read_values_many') as values:
            self.assertIsNone(observer.observe().menu_ready);values.assert_not_called()

    def test_unknown_schema_failure_visible_after_reader_discard(self):
        observer=m.UiAdmissionObserver.__new__(m.UiAdmissionObserver)
        observer.pid=7;observer._reader=N(bind=lambda:nullcontext());observer._ui_controller=(7,4,1,0x10400);observer._ui_local_player=(7,6,1,0x10600)
        observer._discard=Mock()
        with patch.object(m.WarmAdmissionObserver,'observe',return_value=Admission('world_ready','test',('epoch',),True)), \
             patch.object(m,'capture_selected',side_effect=RuntimeQueryError('Invalid class schema')):
            with self.assertRaisesRegex(RuntimeQueryError,'Invalid class schema'):observer.observe()
            observer._discard.assert_called_once_with()


if __name__=='__main__':unittest.main()
