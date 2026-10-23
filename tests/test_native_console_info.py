import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]/'src/expedition33'
def load(name):
    spec=importlib.util.spec_from_file_location('expedition33._native_info_'+name,ROOT/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
m=load('process_console');c=load('_console')

def status(**changes):
    value=dict(version=1,native_version=205,bound=0,disabled=0,unsupported=0,frames=0,fallbacks=0,faults=0)
    value.update(changes);return value

class NativeConsoleInfoTests(unittest.TestCase):
    def setUp(self):
        self.metadata=status();self.commands=[]
        def command(name,*args):
            self.commands.append(name)
            if name=='console-color-status':return dict(console_color_status=dict(self.metadata))
            if name=='console-poll':return dict(console_dropped=0,result=0,console_text='',console_color_status=dict(self.metadata))
            return {}
        self.session=N(_check=Mock(),_transport=N(console_color_status_protocol=1,command=command))
        self.console=c.Console(self.session);self.session.console=self.console;self.console._enabled=True
        self.loader=N(status=lambda:(),discover=lambda:(),_startup_preparations={},_preparation_failures={},
            registry=N(_startup_progress=dict(finished=False)))
        self.menu=N(registry=N(_settings=None),native=None)
        self.driver=m.ProcessConsole(self.session,self.menu)
        self.info=m.StartupConsoleInfo(self.console,self.loader,'0.1.0-test')
        self.console.write=Mock()

    def text(self):return ''.join(call.args[0] for call in self.console.write.call_args_list)

    def test_actual_native_version_queries_once_no_filename_inference(self):
        for _ in range(5):self.driver.poll();self.info.poll(title_ready=True)
        self.assertEqual(self.commands.count('console-color-status'),1)
        self.assertEqual(self.commands.count('console-poll'),5)
        self.assertEqual(self.text().count('[SDK] Native runtime v205 detected'),1)
        self.assertTrue(self.text().startswith('[SDK] ClairObscurSDK v0.1.0-test'))
        self.assertNotIn('colors unavailable',self.text())

    def test_piggyback_fault_warns_once_without_extra_status_ipc(self):
        self.driver.poll();self.info.poll(title_ready=True)
        self.metadata.update(bound=1,disabled=1,faults=1)
        for _ in range(8):self.driver.poll();self.info.poll(title_ready=True)
        self.assertEqual(self.commands.count('console-color-status'),1)
        self.assertEqual(self.commands.count('console-poll'),9)
        self.assertEqual(self.text().count('[WARN] Native console colors unavailable'),1)
        self.assertIn('standard console remains available',self.text())

    def test_capability_absent_or_boolean_never_queries_new_action(self):
        for cap in (0,True,None):
            self.driver._native_status_queried=False
            self.session._transport.console_color_status_protocol=cap
            self.driver.poll()
        self.assertNotIn('console-color-status',self.commands)

    def test_copied_status_does_not_expose_mutable_cache(self):
        self.driver.poll();observed=self.console.native_color_status
        observed['native_version']=999
        self.assertEqual(self.console.native_color_status['native_version'],205)
        self.metadata['native_version']=206
        self.assertEqual(self.console.native_color_status['native_version'],205)

    def test_no_metadata_never_prints_guessed_runtime_version(self):
        self.console._native_color_status=None
        self.info.poll(title_ready=True)
        self.assertIn('Native runtime: initialized',self.text())
        self.assertNotIn('Native runtime v',self.text())

if __name__=='__main__':unittest.main()
