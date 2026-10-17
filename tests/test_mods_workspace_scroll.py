import unittest
from types import SimpleNamespace
from expedition33.mods_workspace_scroll import ScrollWorkspaceView
from expedition33.management import ManagementError
import test_management
from test_mods_workspace import WorkspaceFakePanel

class ScrollFakePanel(WorkspaceFakePanel):
    def __init__(self,session,**options):
        super().__init__(session,**options)
        self.count=105
        self.buttons=list(range(105))
        self.labels=[f'label{i}' for i in range(105)]
        self.summary='summary'
        self.subtitle='subtitle';self.panel_titles=['heading1','heading2','heading3']
    def layout(self,view):pass
    def _render_call(self,*args,**kw):pass
    def scroll_offset(self):return 0.

class ScrollWorkspaceTests(unittest.TestCase):
    setUp=test_management.ManagementTests.setUp
    tearDown=test_management.ManagementTests.tearDown
    def start(self):
        self.view=ScrollWorkspaceView(self.registry)
        self.frame=self.view.render()
    def click(self,label,**kw):
        control=next(c for c in self.frame.controls if c.label==label and c.enabled)
        self.frame=self.view.activate(self.frame.revision,control.token,**kw)
    def test_inline_toggle_keeps_list_and_inspector(self):
        self.start();self.click('OFF')
        self.assertEqual(self.view.screen,'list')
        self.assertTrue(self.registry.view(self.registry.select('specimen'))['enabled'])
        self.assertIn('ON',[c.label for c in self.frame.controls])
        self.click('ON')
        self.assertFalse(self.registry.view(self.registry.select('specimen'))['enabled'])
        self.click('Configure (3 options, 0 keybinds)');self.assertEqual(self.view.screen,'options')
        self.assertEqual(len(self.frame.controls),105)
        self.click('ON')
        self.assertFalse(self.registry.option(self.registry.select('specimen'),'toggle'))
        self.click('Next')
        self.assertEqual(self.registry.option(self.registry.select('specimen'),'choice'),'b')
        self.assertLessEqual(sum(c.enabled for c in self.frame.controls),64)
    def test_conflicts_have_owner_actions_and_resolution(self):
        for name in ('Alpha','Beta'):
            folder=self.root/name;folder.mkdir()
            (folder/'mod.py').write_text("from expedition33.management import ModDefinition,Keybind\nclass Mod:\n def management(self): return ModDefinition('"+name.lower()+"','"+name+"',keybinds=(Keybind('test','Test','F9',lambda arg:None),))\n def enable(self,session): pass\n def disable(self): pass\n")
            self.loader.load(name);self.loader.enable(name)
        self.start();self.click('Conflicts (1)')
        self.assertEqual(self.view.total_rows,2)
        self.assertEqual(sum(c.label=='! F9' for c in self.frame.controls),2)
        self.click('! F9');self.assertEqual(self.view.conflict_key,'F9')
        self.click('Unbind')
        self.assertEqual(self.registry.key_conflicts(),{})
        self.assertEqual(self.view.total_rows,0)
        self.click('All bindings');self.assertEqual(self.view.total_rows,2)
        self.click('Keys: All');self.assertEqual(self.view.total_rows,1)
        self.click('Keys: Bound');self.assertEqual(self.view.total_rows,1)
        self.click('Rebind')
        self.assertEqual(self.view.screen,'all_keys')
        self.assertIn('Press a key',self.frame.status)
        self.assertEqual([c.label for c in self.frame.controls if c.enabled],['Close','Cancel capture'])
        self.click('Cancel capture')
        self.assertIsNone(self.view.capture_target)
        self.assertEqual(self.view.screen,'all_keys')
        from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu
        self.view.selection=self.registry.select('alpha');self.view.screen='options'
        self.frame=self.view.render()
        self.click('Test: Unbound')
        target=self.view.capture_target
        menu=SimpleNamespace(view=self.view,panel=SimpleNamespace(state='open'),refresh=self.view.render)
        ScrollWorkspaceMenu._finish_key_capture(menu,target,'F8')
        self.assertEqual(self.registry.keybind(self.view.selection,'test'),'F8')
        self.assertIn('Test: F8',[c.label for c in self.view.render().controls])
    def test_scroll_window_and_stale_callbacks(self):
        for i in range(20):(self.root/f'Mod{i:02}').mkdir();(self.root/f'Mod{i:02}'/'mod.py').write_text('class Mod: pass')
        self.start();old=self.frame
        self.assertEqual(self.view.total_rows,21)
        self.view.scroll_start=10;self.frame=self.view.render()
        self.assertTrue(self.frame.controls[0].label.startswith('Mod00'))
        self.assertTrue(self.frame.controls[self.view.mod_token(10)].label.startswith('Mod10'))
        self.assertEqual(self.view.scroll_start,0)
        with self.assertRaises(ManagementError):self.view.activate(old.revision,old.controls[0].token)
        self.click('Search',value='specimen')
        self.assertEqual(self.view.scroll_start,0)
        self.assertEqual(self.view.total_rows,1)

    def test_readiness_label_is_registered_as_panel_chrome(self):
        from unittest.mock import Mock
        from expedition33.mods_workspace_scroll import ScrollWorkspacePanel
        panel=Mock()
        panel._text={};panel.readiness_label=SimpleNamespace(index=123)
        panel.panel_titles=[];panel.metadata_labels=[]
        ScrollWorkspacePanel.set_text(panel,panel.readiness_label,'SDK Mods Readiness: 2/9')
        panel._render_call.assert_called_once_with(panel.readiness_label,'TextBlock','SetText',InText='SDK Mods Readiness: 2/9')

    def test_native_mod_scrolling_never_repaints_or_repositions_rows(self):
        from unittest.mock import Mock
        from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu,TEXT_MIN,TEXT_MAX
        for i in range(30):
            folder=self.root/f'Mod{i:02}';folder.mkdir();(folder/'mod.py').write_text('class Mod: pass')
        self.start();revision=self.frame.revision
        panel=Mock(state='open',slider_scale=1.35)
        panel.slider_value.return_value=(1.35-TEXT_MIN)/(TEXT_MAX-TEXT_MIN)
        menu=Mock(panel=panel,view=self.view,failure=None,_presentation_suspended=False)
        for offset in (0,40,320,800,1400,0):
            menu._scroll_poll=0;panel.scroll_offset.return_value=offset
            ScrollWorkspaceMenu.poll_scroll(menu)
            tokens=self.view.bindable_tokens()
            self.assertLessEqual(sum(c.enabled and c.token in tokens for c in self.frame.controls),64)
        menu.refresh.assert_not_called()
        self.assertEqual(self.view._revision,revision)
        self.assertEqual(self.view.scroll_start,0)

    def test_settings_scroll_recycles_actions_for_correct_option(self):
        folder=self.root/'ManySettings';folder.mkdir()
        (folder/'mod.py').write_text("from expedition33.management import ModDefinition,Option\nclass Mod:\n def management(self): return ModDefinition('many','Many settings',options=tuple(Option('opt'+str(i),'Option '+str(i),'bool',False) for i in range(20)))\n def enable(self,session): pass\n def disable(self): pass\n")
        self.loader.load('ManySettings')
        self.start();self.view.selection=self.registry.select('many');self.view.screen='options'
        self.frame=self.view.render();old=self.frame
        self.assertEqual(self.view.total_rows,20)
        self.view.scroll_start=10;self.frame=self.view.render()
        self.assertTrue(self.frame.controls[0].label.startswith('Option 10:'))
        with self.assertRaises(ManagementError):self.view.activate(old.revision,old.controls[1].token)
        self.click('OFF')
        self.assertTrue(self.registry.option(self.registry.select('many'),'opt10'))
        self.assertFalse(self.registry.option(self.registry.select('many'),'opt0'))

    def test_independent_key_scroll_keeps_options_and_bounds_active_controls(self):
        folder=self.root/'Dual';folder.mkdir()
        (folder/'mod.py').write_text("from expedition33.management import ModDefinition,Option,Keybind\nclass Mod:\n def management(self): return ModDefinition('dual','Dual',options=tuple(Option('o'+str(i),'Option '+str(i),'bool',False) for i in range(30)),keybinds=tuple(Keybind('k'+str(i),'Key '+str(i),None,lambda _:None) for i in range(30)))\n def enable(self,session): pass\n def disable(self): pass\n")
        self.loader.load('Dual');self.start()
        self.view.selection=self.registry.select('dual');self.view.screen='options'
        self.view.scroll_start=6;self.view.key_scroll_start=15;self.frame=self.view.render()
        self.assertTrue(self.frame.controls[0].label.startswith('Option 6:'))
        self.assertTrue(self.frame.controls[64].label.startswith('Key 15:'))
        self.assertLessEqual(sum(c.enabled for c in self.frame.controls),64)
        self.click('Key 15: Unbound')
        self.assertEqual(self.view.capture_target[1],'k15')
        self.click('Cancel capture')
        self.assertEqual((self.view.scroll_start,self.view.key_scroll_start),(6,15))

if __name__=='__main__':unittest.main()
