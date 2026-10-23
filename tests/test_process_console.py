import importlib.util
from pathlib import Path
import threading
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch
from expedition33._console import Console
from expedition33.management import ModDefinition
from expedition33 import RuntimeQueryError

SOURCE=Path(__file__).resolve().parents[1]/'src/expedition33/process_console.py'
spec=importlib.util.spec_from_file_location('expedition33._process_console_candidate',SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        class Session:
            def __init__(self):
                self.owner=threading.get_ident();self._transport=N(command=Mock(return_value={}))
                self.poll=Mock()
            def _check(self):
                if threading.get_ident()!=self.owner:raise RuntimeError('Session owner thread')
        self.session=Session();self.session.console=Console(self.session)
        self.registry=N(_settings=None,stage_enabled=Mock(),stage_option=Mock(),request_shutdown=Mock())
        self.native=object();self.menu=N(registry=self.registry,native=self.native)
        self.driver=m.ProcessConsole(self.session,self.menu)

    def test_false_and_uncertain_readiness_never_attach(self):
        self.driver.enable_for_title(False);self.driver.enable_for_title(None)
        self.session._transport.command.assert_not_called()

    def test_verified_title_attaches_once_then_delivers_without_gameplay_poll(self):
        self.driver.enable_for_title(True);self.driver.enable_for_title(True)
        commands=[call.args[0] for call in self.session._transport.command.call_args_list]
        self.assertEqual(commands.count('console-attach'),1)
        self.session._transport.command.return_value=dict(console_dropped=0,result=0)
        self.assertEqual(self.driver.poll(),())
        self.session.poll.assert_not_called()
        self.assertEqual(self.session._transport.command.call_args.args[0],'console-poll')

    def test_title_management_stages_and_shutdown_remains_process_level(self):
        selection=N(mod_id='example')
        self.menu.registry.set_enabled(selection,True)
        self.registry.stage_enabled.assert_called_once_with(selection,True)
        self.menu.registry.set_option(selection,'option',3)
        self.registry.stage_option.assert_called_once_with(selection,'option',3,reset=False)
        self.menu.registry.request_shutdown();self.registry.request_shutdown.assert_called_once_with()
        self.assertIsNone(self.menu.native)

    def test_world_admission_restores_original_registry_without_enabling_mods(self):
        self.driver.world_active()
        self.assertIs(self.menu.registry,self.registry);self.assertIs(self.menu.native,self.native)
        self.session._transport.command.assert_not_called()

    def test_attach_failure_never_automatically_replayed(self):
        self.session._transport.command.side_effect=RuntimeQueryError('uncertain attach')
        with self.assertRaises(RuntimeQueryError):self.driver.enable_for_title(True)
        with self.assertRaisesRegex(RuntimeError,'no automatic replay'):self.driver.enable_for_title(True)
        self.assertEqual(self.session._transport.command.call_count,1)

    def test_worker_cannot_attach_poll_or_restore_routing(self):
        errors=[]
        def worker():
            for callback in (lambda:self.driver.enable_for_title(True),self.driver.poll,self.driver.world_active):
                try:callback()
                except RuntimeError as error:errors.append(error)
        thread=threading.Thread(target=worker);thread.start();thread.join()
        self.assertEqual(len(errors),3);self.session._transport.command.assert_not_called()


class StartupInfoTests(unittest.TestCase):
    def setUp(self):
        self.console=N(_enabled=False,write=Mock())
        self.progress=dict(completed=0,total=1,failed=0,finished=False)
        self.rows=[N(name='ExampleCore',enabled=True,preparation_error=None,cleanup_error=None)]
        self.loader=N(status=lambda:tuple(self.rows),discover=lambda:('ExampleCore','ExampleWorld'),
            _startup_preparations={'ExampleCore':object()},_preparation_failures={},
            registry=N(_startup_progress=self.progress))
        self.info=m.StartupConsoleInfo(self.console,self.loader,'0.1.0-test')

    def text(self):return ''.join(call.args[0] for call in self.console.write.call_args_list)

    def test_title_block_actual_counts_once_and_no_unattached_output(self):
        self.info.poll(title_ready=True);self.console.write.assert_not_called()
        self.console._enabled=True
        self.info.poll(title_ready=True);calls=self.console.write.call_count
        for _ in range(20):self.info.poll(title_ready=True)
        self.assertEqual(calls,self.console.write.call_count)
        for line in ('[SDK] ClairObscurSDK v0.1.0-test','Game state: TITLE_SCREEN',
                'Mod discovery: 2 packages found','World-dependent activation: deferred',
                'SDK READY — awaiting gameplay world','Console ready. Type help for commands.'):
            self.assertIn(line,self.text())
        self.assertNotIn('GAMEPLAY READY',self.text())

    def test_world_success_and_completion_are_separate_once_transitions(self):
        self.console._enabled=True
        self.info.poll(title_ready=True);self.info.poll(world_active=True)
        self.info.activation('ExampleWorld',True);self.info.activation('ExampleWorld',True)
        self.assertEqual(self.text().count('ExampleWorld: activated'),1)
        self.assertNotIn('GAMEPLAY READY',self.text())
        self.progress.update(completed=1,finished=True)
        self.info.poll(world_active=True);self.info.poll(world_active=True)
        self.assertEqual(self.text().count('World readiness validated'),1)
        self.assertEqual(self.text().count('GAMEPLAY READY'),1)

    def test_failures_explicit_without_error_payload_or_preferences(self):
        self.console._enabled=True
        self.loader._preparation_failures={'ExampleWorld':'do not print this payload'}
        self.progress.update(completed=1,failed=1,finished=True)
        self.info.activation('ExampleWorld',False);self.info.poll(world_active=True)
        self.assertIn('Early preparation: finished with failures',self.text())
        self.assertIn('[ERROR] ExampleWorld: activation failed',self.text())
        self.assertIn('GAMEPLAY READY WITH MOD FAILURES',self.text())
        self.assertNotIn('do not print this payload',self.text())

    def test_enable_times_keep_semantic_colors_and_count_each_result_once(self):
        self.console._enabled=True
        self.info.activation('Fast',True,16.25)
        self.info.activation('Fast',True,999)
        self.info.activation('Failed',False,1200.0)
        self.info.activation('Slow',True,412.8)
        self.assertNotIn(' ms',self.text())
        self.info.command()
        self.assertIn('[OK] Fast: preparation unreported | activation 16.2 ms',self.text())
        self.assertIn('[ERROR] Failed: preparation unreported | activation 1200.0 ms',self.text())
        self.assertIn('[WAIT] Slow: preparation unreported | activation 412.8 ms',self.text())
        self.progress.update(completed=2,total=2,failed=1,finished=True)
        self.info.poll(world_active=True)
        self.assertIn('[INFO] Total activation work: 1629.0 ms',self.text())
        self.assertNotIn('999',self.text())

    def test_invalid_enable_times_are_rejected_before_output(self):
        self.console._enabled=True
        for value in (-1,float('nan'),float('inf'),True,'1'):
            with self.assertRaises(ValueError):self.info.activation('Invalid',True,value)
        self.console.write.assert_not_called()

    def test_usable_is_separate_from_enable_and_waits_for_explicit_signal(self):
        self.console._enabled=True
        ready=Mock(return_value=False)
        self.loader._loaded={'ExampleWorld':(None,N(startup_ready=ready),object())}
        self.loader.registry._entries={'example':N(name='ExampleWorld',definition=ModDefinition('example','Example'))}
        self.loader.registry._startup_activation_started={'example':10.0}
        self.info.activation('Example',True,20.0)
        with patch.object(m.time,'perf_counter',return_value=13.0):
            self.info.poll(world_active=True)
            self.assertNotIn('Example: usable',self.text())
            ready.return_value=True
            self.info.poll(world_active=True);self.info.poll(world_active=True)
        self.assertNotIn('3000.0 ms',self.text())
        self.info.command()
        self.assertIn('usable 3000.0 ms',self.text())

    def test_no_readiness_callback_reports_unreported_instead_of_guessing(self):
        self.console._enabled=True
        self.loader._loaded={'Legacy':(None,N(),object())}
        self.loader.registry._entries={'legacy':N(name='Legacy',definition=ModDefinition('legacy','Legacy'))}
        self.loader.registry._startup_activation_started={'legacy':10.0}
        self.info.activation('Legacy',True,1.0)
        self.info.poll(world_active=True);self.info.poll(world_active=True)
        self.assertNotIn('usable unreported',self.text())
        self.info.command()
        self.assertEqual(self.text().count('usable unreported'),1)

    def test_timing_command_does_not_reenable_or_query_readiness(self):
        self.console._enabled=True
        self.info.activation('Example',True,12.5,24.0)
        before=self.text()
        self.assertNotIn('12.5',before)
        self.info.command();self.info.command()
        self.assertEqual(self.text().count('preparation 24.0 ms | activation 12.5 ms'),2)
        count=self.console.write.call_count
        self.assertEqual(self.info.command('on'),'Usage: startuptiming')
        self.assertEqual(self.console.write.call_count,count)

    def test_new_world_cycle_resets_report_without_reprinting_bootstrap(self):
        self.console._enabled=True
        self.info.poll(world_active=True)
        self.info.activation('Example',True,12.0,24.0)
        self.info.begin_world_cycle()
        self.info.activation('Example',True,3.0,24.0)
        self.info.poll(world_active=True)
        self.info.command()
        self.assertEqual(self.text().count('ClairObscurSDK v'),1)
        self.assertIn('Total activation work: 3.0 ms',self.text())
        self.assertNotIn('activation 12.0 ms',self.text())

    def test_degraded_title_warning_once_preserves_core_console_readiness(self):
        self.console._enabled=True
        self.info.poll(title_ready=True)
        for _ in range(20):self.info.poll(title_ready=True,frontend_failed=True)
        self.assertEqual(self.text().count('[WARN] Title frontend unavailable'),1)
        self.assertIn('SDK core and console remain available',self.text())


if __name__=='__main__':unittest.main()
