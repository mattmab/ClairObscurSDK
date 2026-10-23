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
    def layout(self,view):
        if len(self.buttons)<self.count:
            self.buttons=list(range(self.count))
            self.labels=[f'label{i}' for i in range(self.count)]
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

    def test_fixed_global_key_rows_keep_all_actions_and_scroll_only_rebinds(self):
        from unittest.mock import Mock
        from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu,TEXT_MIN,TEXT_MAX,key_token
        folder=self.root/'ManyKeys';folder.mkdir()
        (folder/'mod.py').write_text("from expedition33.management import ModDefinition,Keybind\nclass Mod:\n def management(self): return ModDefinition('manykeys','Many Keys',keybinds=tuple(Keybind('k'+str(i),'Key '+str(i),None,lambda _:None) for i in range(30)))\n def enable(self,session): pass\n def disable(self): pass\n")
        self.loader.load('ManyKeys');self.start()
        self.view.screen='all_keys';self.view.key_row_capacity=40
        self.frame=self.view.render();revision=self.frame.revision
        self.assertEqual(self.view.total_rows,30)
        for row in range(30):
            self.assertEqual([c.label for c in self.frame.controls[key_token(row)+2:key_token(row)+6]],['Rebind','Unbind','Disable mod','Reset'])
        panel=Mock(state='open',slider_scale=1.35)
        panel.slider_value.return_value=(1.35-TEXT_MIN)/(TEXT_MAX-TEXT_MIN)
        menu=Mock(panel=panel,view=self.view,failure=None,_presentation_suspended=False)
        for offset in (0,84,840,1800,0):
            menu._scroll_poll=0;panel.scroll_offset.return_value=offset
            ScrollWorkspaceMenu.poll_scroll(menu)
            tokens=self.view.bindable_tokens()
            self.assertLessEqual(sum(c.enabled and c.token in tokens for c in self.frame.controls),64)
        menu.refresh.assert_not_called();panel.position.assert_not_called()
        self.assertEqual(self.view._revision,revision)
        self.assertEqual(self.view.scroll_start,0)

    def test_differential_scroll_retains_callbacks_and_failed_remove_never_binds_entered(self):
        from unittest.mock import Mock
        from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu,key_token
        from expedition33.mods_workspace import ModsWorkspaceMenu
        folder=self.root/'WindowKeys';folder.mkdir()
        (folder/'mod.py').write_text("from expedition33.management import ModDefinition,Keybind\nclass Mod:\n def management(self): return ModDefinition('windowkeys','Window Keys',keybinds=tuple(Keybind('k'+str(i),'Key '+str(i),None,lambda _:None) for i in range(30)))\n def enable(self,session): pass\n def disable(self): pass\n")
        self.loader.load('WindowKeys');self.start();self.view.screen='all_keys';self.view.key_row_capacity=40
        self.frame=self.view.render()
        native=Mock();native.bind_controls.side_effect=lambda pairs:[object() for _ in pairs];native.remove_controls.return_value=True
        menu=ScrollWorkspaceMenu.__new__(ScrollWorkspaceMenu)
        menu.frame=self.frame;menu.view=self.view;menu.panel=SimpleNamespace(buttons=list(range(len(self.frame.controls))),menu=native)
        menu.actions=[];menu._presentation_suspended=False;menu._sync_key_capture=lambda:None
        menu._bind();initial=dict(menu._binding_tokens)
        self.view.update_scroll_bindings(1);menu._rebind_scroll_window()
        for token in set(initial)&set(menu._binding_tokens):self.assertIs(initial[token],menu._binding_tokens[token])
        self.assertEqual(native.remove_controls.call_args[0][0],[initial[key_token(0)+c] for c in range(6) if key_token(0)+c in initial])
        previous=dict(menu._binding_tokens);owners=list(menu.actions);before=native.bind_controls.call_count
        native.remove_controls.return_value=False;self.view.update_scroll_bindings(2)
        with self.assertRaisesRegex(RuntimeError,'retain all owners'):menu._rebind_scroll_window()
        self.assertEqual(menu._binding_tokens,previous);self.assertEqual(menu.actions,owners)
        self.assertEqual(native.bind_controls.call_count,before)

    def test_options_key_scrolling_only_rebinds_fixed_column(self):
        from unittest.mock import Mock
        from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu,TEXT_MIN,TEXT_MAX
        self.start();self.view.screen='options';self.view.key_total=30;self.view.total_rows=0
        panel=Mock(state='open',slider_scale=1.35)
        panel.slider_value.return_value=(1.35-TEXT_MIN)/(TEXT_MAX-TEXT_MIN)
        panel.scroll_offset.return_value=0
        menu=Mock(panel=panel,view=self.view,failure=None,_presentation_suspended=False)
        for offset in (0,640,1200,0):
            panel.key_scroll_offset.return_value=offset;menu._scroll_poll=0
            ScrollWorkspaceMenu.poll_scroll(menu)
        menu.refresh.assert_not_called();panel.position.assert_not_called()
        self.assertEqual(self.view.key_scroll_start,0)

    def test_independent_key_scroll_keeps_options_and_bounds_active_controls(self):
        folder=self.root/'Dual';folder.mkdir()
        (folder/'mod.py').write_text("from expedition33.management import ModDefinition,Option,Keybind\nclass Mod:\n def management(self): return ModDefinition('dual','Dual',options=tuple(Option('o'+str(i),'Option '+str(i),'bool',False) for i in range(30)),keybinds=tuple(Keybind('k'+str(i),'Key '+str(i),None,lambda _:None) for i in range(30)))\n def enable(self,session): pass\n def disable(self): pass\n")
        self.loader.load('Dual');self.start()
        self.view.selection=self.registry.select('dual');self.view.screen='options';self.view.key_row_capacity=40
        self.view.scroll_start=6;self.view.key_scroll_start=15;self.frame=self.view.render()
        self.assertTrue(self.frame.controls[0].label.startswith('Option 6:'))
        from expedition33.mods_workspace_scroll import column_key_token
        self.assertTrue(self.frame.controls[column_key_token(15,40)].label.startswith('Key 15:'))
        self.assertLessEqual(sum(c.enabled and c.token in self.view.bindable_tokens() for c in self.frame.controls),64)
        self.click('Key 15: Unbound')
        self.assertEqual(self.view.capture_target[1],'k15')
        self.click('Cancel capture')
        self.assertEqual((self.view.scroll_start,self.view.key_scroll_start),(6,15))

if __name__=='__main__':unittest.main()


class ScrollGeometryCacheTests(unittest.TestCase):
    def panel(self):
        from expedition33.mods_workspace_scroll import ScrollWorkspacePanel
        from unittest.mock import Mock
        panel=object.__new__(ScrollWorkspacePanel)
        panel.appearance=('World Builder',1.)
        panel._scaled_geometry={};panel._slot_geometry={};panel._readiness_visible=None
        panel.slider_scale=1.;panel.slider='slider';panel.scale_label='scale'
        panel.scaled_labels=[(SimpleNamespace(index=1),.5),(SimpleNamespace(index=2),.4)]
        panel.text_bounds={1:('slot1',200.,50.),2:('slot2',300.,60.)}
        panel._render_call=Mock();panel.set_text=Mock()
        panel.readiness_label='label';panel.readiness_track='track';panel.readiness_fill='fill'
        panel.invisible='visible';panel.collapsed='collapsed'
        return panel

    def test_unchanged_scale_has_no_geometry_setters_but_resized_label_updates(self):
        from unittest.mock import patch
        from expedition33.mods_workspace import ModsWorkspacePanel
        panel=self.panel()
        with patch.object(ModsWorkspacePanel,'paint_appearance',lambda owner,theme,scale:setattr(owner,'appearance',(theme,scale))):
            panel.paint_appearance('World Builder',1.)
            self.assertEqual(panel._render_call.call_count,4)
            panel._render_call.reset_mock()
            panel.paint_appearance('World Builder',1.)
            self.assertEqual(panel._render_call.call_count,0)
            panel.text_bounds[2]=('slot2',310.,60.)
            panel.paint_appearance('World Builder',1.)
            self.assertEqual(panel._render_call.call_count,2)
            self.assertEqual(panel._render_call.call_args.args[:3],('slot2','CanvasPanelSlot','SetSize'))

    def test_permanent_slot_skips_unchanged_planning_and_tracks_exact_identity(self):
        panel=self.panel();panel.scaled_labels=[]
        slot=SimpleNamespace(index=9,serial=4,address=123)
        panel.position(slot,0,10,200,40)
        self.assertEqual(panel._render_call.call_count,2)
        panel.position(slot,0,10,200,40)
        self.assertEqual(panel._render_call.call_count,2)
        panel.position(slot,0,11,200,40)
        self.assertEqual(panel._render_call.call_count,4)
        replacement=SimpleNamespace(index=9,serial=5,address=124)
        panel.position(replacement,0,11,200,40)
        self.assertEqual(panel._render_call.call_count,6)

    def test_visibility_is_queued_once_and_failed_batch_invalidates_tentative_cache(self):
        from unittest.mock import patch
        from contextlib import contextmanager
        from expedition33.widgets import OwnedMenuPanel
        panel=self.panel()
        @contextmanager
        def rejected(owner):
            yield
            raise RuntimeError('ACK unknown')
        with patch.object(OwnedMenuPanel,'paint_batch',rejected):
            with self.assertRaisesRegex(RuntimeError,'ACK unknown'):
                with panel.paint_batch():
                    panel.set_readiness_visible(True)
                    panel.set_readiness_visible(True)
                    panel._scaled_geometry[1]=('tentative',)
            self.assertEqual(panel._render_call.call_count,3)
            self.assertIsNone(panel._readiness_visible)
            self.assertEqual(panel._scaled_geometry,{})
        panel.set_readiness_visible(True)
        self.assertEqual(panel._render_call.call_count,6)
