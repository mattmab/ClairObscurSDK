import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock
from expedition33.settings import SettingsStore

SOURCE=Path(__file__).resolve().parents[1]/'src/expedition33/management.py'
spec=importlib.util.spec_from_file_location('expedition33._title_management_candidate',SOURCE)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=SettingsStore(Path(self.temp.name)/'management.json')
        self.callback=Mock()
        self.definitions={'Prepared':m.ModDefinition('prepared','Prepared',options=(
            m.Option('count','Count','int',2,minimum=1,maximum=5,on_change=self.callback),)),
            'Legacy':m.ModDefinition('legacy','Legacy'),'Later':m.ModDefinition('later','Later'),
            'Core':m.ModDefinition('core','Core',protected=True)}
        class Loader:
            def __init__(self,outer):self.outer=outer;self.active=set();self.calls=[]
            def discover(self):return tuple(self.outer.definitions)
            def status(self):return tuple(N(name=name,enabled=name in self.active) for name in self.outer.definitions)
            def load(self,name):
                self.calls.append(('load',name))
                if not any(e.name==name for e in self.registry._entries.values()):
                    self.registry.register(name,self.outer.definitions[name])
            def enable(self,name):self.calls.append(('enable',name));self.active.add(name)
            def disable(self,name):self.calls.append(('disable',name));self.active.discard(name)
        self.loader=Loader(self);self.registry=m.Registry(self.loader,self.store);self.loader.registry=self.registry
        self.registry.register('Prepared',self.definitions['Prepared'])

    def test_stage_choice_changes_desired_not_actual_or_callbacks(self):
        old=self.registry.select('prepared')
        new=self.registry.stage_enabled(old,True)
        view=self.registry.view(new)
        self.assertTrue(view['desired_enabled']);self.assertFalse(view['enabled']);self.assertTrue(view['staged_pending'])
        self.assertEqual(self.loader.calls,[]);self.assertTrue(self.store.get('prepared')['enabled'])
        with self.assertRaises(m.ManagementError):self.registry.view(old)

    def test_stage_disable_active_mod_does_not_cleanup(self):
        self.loader.active.add('Prepared')
        selected=self.registry.stage_enabled(self.registry.select('prepared'),False)
        self.assertTrue(self.registry.view(selected)['enabled'])
        self.assertFalse(self.registry.view(selected)['desired_enabled'])
        self.assertEqual(self.loader.calls,[])

    def test_stage_option_skips_callback_even_for_active_mod(self):
        self.loader.active.add('Prepared')
        self.registry.stage_option(self.registry.select('prepared'),'count',4)
        self.callback.assert_not_called()
        self.assertEqual(self.store.get('prepared')['options']['count'],4)
        with self.assertRaises(m.ManagementError):self.registry.stage_option(self.registry.select('prepared'),'count',99)

    def test_unimported_saved_legacy_toggle_does_not_load(self):
        self.store.save('legacy',dict(enabled=False,folder='Legacy'))
        self.assertEqual(self.registry.stage_saved_enabled('legacy',True),'legacy')
        self.assertTrue(self.store.get('legacy')['enabled']);self.assertEqual(self.loader.calls,[])
        self.assertNotIn('legacy',self.registry._entries)

    def test_unknown_identity_and_protected_disable_rejected(self):
        with self.assertRaises(m.ManagementError):self.registry.stage_saved_enabled('unknown',True)
        self.registry.register('Core',self.definitions['Core'])
        with self.assertRaises(m.ManagementError):self.registry.stage_enabled(self.registry.select('core'),False)

    def test_generator_created_before_title_edits_uses_latest_choices(self):
        steps=self.registry.restore_enabled_steps()
        self.store.save('legacy',dict(enabled=False,folder='Legacy'))
        self.registry.stage_saved_enabled('legacy',True)
        self.assertEqual(list(steps),[('legacy',None)])
        self.assertIn(('enable','Legacy'),self.loader.calls)

    def test_intervening_disable_and_newly_added_id_respected(self):
        self.store.save('legacy',dict(enabled=True,folder='Legacy'))
        self.registry.stage_enabled(self.registry.select('prepared'),True)
        self.registry._startup_order.save(['prepared','legacy','later'])
        steps=self.registry.restore_enabled_steps()
        self.assertEqual(next(steps),('prepared',None))
        self.registry.stage_saved_enabled('legacy',False)
        self.store.save('later',dict(enabled=True,folder='Later'))
        self.assertEqual(list(steps),[('later',None)])
        self.assertNotIn(('load','Legacy'),self.loader.calls)

    def test_attempted_failure_never_replayed_after_new_stage(self):
        self.store.save('missing',dict(enabled=True,folder='Missing'))
        steps=self.registry.restore_enabled_steps()
        self.assertEqual(next(steps)[0],'missing')
        self.store.save('missing',dict(enabled=True,folder='Missing'))
        self.assertEqual(list(steps),[])


if __name__=='__main__':unittest.main()
