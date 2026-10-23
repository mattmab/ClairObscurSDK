"""Isolated title management + attachment protocol tests, no live operations."""
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import patch
import unittest
import test_management
from expedition33.title_management import TitleWorkspaceView,TitleRegistryFacade
from expedition33.title_menu import TitleMenuEntry,TITLE_WORLD
from expedition33.management import ManagementError

class TitleManagementTests(unittest.TestCase):
 setUp=test_management.ManagementTests.setUp
 tearDown=test_management.ManagementTests.tearDown
 def test_desired_toggle_never_enables_gameplay(self):
  facade=TitleRegistryFacade(self.registry);selection=facade.select('specimen')
  with patch.object(self.loader,'enable',side_effect=AssertionError('gameplay enable')):selection=facade.set_enabled(selection,True)
  row=facade.view(selection);self.assertTrue(row['enabled']);self.assertFalse(row['active_enabled']);self.assertTrue(self.store.get('specimen')['enabled'])
 def test_options_stage_without_callbacks_even_active(self):
  self.loader.enable('Specimen');instance=self.loader._loaded['Specimen'][1];before=instance.value
  facade=TitleRegistryFacade(self.registry);facade.set_option(facade.select('specimen'),'count',7)
  self.assertEqual(instance.value,before);self.assertEqual(self.store.get('specimen')['options']['count'],7)
 def test_view_toggle_and_config_refresh_generation(self):
  view=TitleWorkspaceView(self.registry);frame=view.render();control=next(c for c in frame.controls if c.label=='OFF');frame=view.activate(frame.revision,control.token)
  self.assertTrue(self.store.get('specimen')['enabled']);self.assertFalse(self.loader.status()[0].enabled)
  self.assertIn('after loading',frame.status)
  self.assertFalse(any(c.enabled for c in frame.controls if view._commands.get(c.token,('',))[0]=='reload_current'))
 def test_legacy_saved_folder_stages_without_import(self):
  folder=self.root/'Legacy';folder.mkdir();(folder/'mod.py').write_text("raise AssertionError('must remain deferred')")
  self.store.save('legacy.id',{'folder':'Legacy','enabled':False})
  view=TitleWorkspaceView(self.registry);frame=view.render();control=next(c for c in frame.controls if view._commands.get(c.token)==('title_legacy','Legacy',True));frame=view.activate(frame.revision,control.token)
  self.assertIn('Definition deferred',frame.description);control=next(c for c in frame.controls if c.label=='Enable after loading');view.activate(frame.revision,control.token)
  self.assertTrue(self.store.get('legacy.id')['enabled']);self.assertNotIn('Legacy',self.loader._loaded)
 def test_unknown_legacy_identity_cannot_guess_saved_id(self):
  facade=TitleRegistryFacade(self.registry)
  with self.assertRaisesRegex(ManagementError,'known saved identity'):facade.stage_saved('Unknown',True)
 def test_gameplay_actions_blocked(self):
  facade=TitleRegistryFacade(self.registry)
  for name in ('invoke','load','reload_current','unload','install_staged'):
   with self.assertRaisesRegex(ManagementError,'after loading'):getattr(facade,name)('anything')
 def test_reopen_view_unwraps_facade(self):
  view=TitleWorkspaceView(self.registry);view.close();reopened=TitleWorkspaceView(view.registry)
  self.assertIs(reopened.registry._registry,self.registry);self.assertTrue(reopened.render().controls)

class TitleAttachmentTests(unittest.TestCase):
 def setUp(self):
  self.events=[];self.ready=True
  self.parent=N(pid=7,_session=N(_transport=N(pause_attachment_protocol=2,trace_renew_protocol=1)))
  self.service=N(menu=None,open=lambda:self.events.append('open'))
  self.entry=TitleMenuEntry(self.parent,self.service,readiness=lambda:self.ready)
  self.scope=N(_session=self.parent._session,_leases=[],invocation_planner=lambda **kw:self.planner,retain=lambda obj:N(object=obj,active=True),close=lambda:self.events.append('scope-close'))
  self.planner=N(_catalog=None,prepare=lambda *a,**kw:N(_plan=object(),invoke=lambda:nullcontext(N(return_value=True))))
  def obj(name,index):return N(name=name,index=index,serial=1,address=index+1000,class_name=name)
  self.player=obj('PlayerController',1);self.title=obj('WBP_MM_TitleScreen_C',2);self.box=obj('VerticalBox',3);self.button=obj('WBP_BaseButton_C',4);self.style=obj('style',5)
  self.catalog=N(objects=[obj('Default__WidgetBlueprintLibrary',20),obj('Default__GameplayStatics',21)],with_observations=lambda value:self.catalog)
  self.planner._catalog=self.catalog
  self.found=dict(context={'world_path':TITLE_WORLD,'controller':(7,1,1,1001),'world':(7,9,1,1009)},catalog=self.catalog,local_player=obj('LocalPlayer',9),player=self.player,main=obj('main',8),title=self.title,box=self.box,restore_tree=obj('WidgetTree',40),restore_panel=obj('Overlay',41),source_button=obj('source',6),source_slot=obj('source-slot',7),style=self.style)
 def install(self,changed=False):
  import expedition33.title_menu as module
  self.entry.cls=lambda name:N(index={'CommonButtonBase':10,'VerticalBoxSlot':11}.get(name,12))
  self.entry.fn=lambda owner,name:name
  self.entry._prepare_title_input=lambda:'typed-uionly-plan'
  self.entry.reference=lambda obj,owner,name:N(name=name,index=60,serial=1,address=1060)
  self.entry.layout=lambda *a,**kw:self.events.append('layout')
  self.getter_targets=[]
  def call(obj,owner,name,**kw):
   if name in ('GetRenderOpacity','GetIsEnabled'):self.getter_targets.append((name,obj))
   return 1. if name=='GetRenderOpacity' else True
  self.entry.call=call
  self.entry.flush_layout=lambda:self.events.append('flush')
  self.entry._current_title=lambda:not changed
  self.entry.one=lambda rows:next(iter(rows))
  def create(obj,owner,name,**kw):
   self.events.append(name)
   if name=='Create':self.scope._leases.append(N(active=True,object=self.button));return self.button
   return N(index=50,serial=1,address=1050)
  self.entry.create=create
  attachment=N(arm=lambda *a:self.events.append('arm-remove'),arm_restore=lambda *a:self.events.append('arm-restore'),close=lambda:self.events.append('detach') or True)
  observer=N(close=lambda:self.events.append('observer-close'),read=lambda:(),state='active')
  dimensions=N(values={(10,'MinWidth'):300.,(10,'MinHeight'):60.})
  padding=N(values={(11,'Padding'):N(fields={'Left':0.,'Top':0.,'Right':0.,'Bottom':0.})})
  def values(catalog,objects,**kw):return {objects[0].index:dimensions if objects[0].index==6 else padding}
  with patch.object(module,'ReadBatch',lambda *a,**kw:nullcontext()),patch.object(module,'resolve_title',return_value=self.found),patch.object(module,'capture_matching',return_value=self.catalog),patch.object(module,'SessionScope',return_value=self.scope),patch.object(module,'PauseAttachment',return_value=attachment),patch.object(module,'PauseClicks',return_value=observer),patch.object(module,'prepare_call',return_value='remove-plan'),patch.object(module,'read_values_many',side_effect=values),patch.object(module,'replace',lambda obj,**kw:obj):return self.entry.install()
 def test_arms_native_cleanup_before_borrowed_parent_attachment(self):
  self.assertTrue(self.install());self.assertLess(self.events.index('arm-remove'),self.events.index('AddChildToVerticalBox'));self.assertLess(self.events.index('arm-restore'),self.events.index('AddChildToVerticalBox'));self.assertEqual(self.entry.state,'attached');self.assertEqual(self.getter_targets,[('GetRenderOpacity',self.found['restore_panel']),('GetIsEnabled',self.found['restore_panel'])]);self.assertIs(self.entry.pause,self.title)
 def test_context_changed_before_append_retains_created_owner(self):
  with self.assertRaisesRegex(RuntimeError,'Title changed'):self.install(changed=True)
  self.assertNotIn('AddChildToVerticalBox',self.events);self.assertIs(self.entry.scope,self.scope);self.assertIsNotNone(self.entry.attachment)
 def test_not_ready_does_not_construct(self):
  self.ready=False
  with patch('expedition33.title_menu.resolve_title',side_effect=AssertionError('read while inactive')):self.assertFalse(self.entry.install())
  self.assertEqual(self.events,[])
 def test_title_exit_closes_entry_not_gameplay(self):
  self.install();self.ready=False;self.entry.poll();self.assertEqual(self.events[-3:],['observer-close','detach','scope-close']);self.assertEqual(self.entry.state,'closed')
 def test_open_rejects_changed_title(self):
  self.entry._current_title=lambda:False
  with self.assertRaisesRegex(RuntimeError,'changed'):self.entry.open()
  self.assertEqual(self.events,[])


class TitleAuthorityTests(unittest.TestCase):
 def setUp(self):
  self.scope=N(pid=7)
  def obj(i,cls):return N(index=i,serial=1,address=1000+i,class_name=cls)
  self.local=obj(1,'LocalPlayer');self.player=obj(2,'BP_jRPG_Controller_MainMenu_C');self.main=obj(3,'WBP_MM_MainMenu_C');self.title=obj(4,'WBP_MM_TitleScreen_C');self.box=obj(5,'VerticalBox');self.world=obj(6,'World')
  identity=lambda o:(o.index,o.serial,o.address)
  context=dict(controller=(7,*identity(self.player)),world=(7,*identity(self.world)),world_path=TITLE_WORLD)
  self.binding=(context,identity(self.local),identity(self.main),identity(self.title),identity(self.box))
  self.catalog=N(by_index={o.index:o for o in (self.local,self.player,self.main,self.title,self.box,self.world)},outer_chain=lambda obj:[self.world],path_name=lambda obj:TITLE_WORLD)
  self.values={}
  for obj,fields in ((self.local,{'PlayerController':self.player}),(self.player,{'Player':self.local,'MainMenuWidgetReference':self.main}),(self.main,{'TitleScreen':self.title}),(self.title,{'ButtonsBox':self.box})):
   self.values[obj.index]=N(types={(0,k):'ObjectProperty' for k in fields},values={(0,k):v for k,v in fields.items()},errors={},truncated=set())
 def run_check(self,*,expected_reads=1,**extra):
  import expedition33.title_menu as module
  with patch.object(module,'ReadBatch',lambda *a,**k:nullcontext()),patch.object(module,'capture_selected',return_value=self.catalog) as capture,patch.object(module,'read_values_many',return_value=self.values) as reads,patch.object(module,'capture_matching',side_effect=AssertionError('no global discovery')):
   result=module.title_authority_current(self.scope,self.binding,**extra)
   self.assertEqual(capture.call_count,1);self.assertEqual(reads.call_count,expected_reads)
   if expected_reads:self.assertEqual(set(reads.call_args.kwargs['fields']),{'PlayerController','Player','MainMenuWidgetReference','TitleScreen','ButtonsBox'}|({'WidgetTree','RootWidget'} if extra else set()))
   return result
 def test_hot_authority_two_bounded_queries(self):self.assertTrue(self.run_check())
 def test_replacement_controller_does_not_inherit_title_authority(self):
  self.values[1].values[(0,'PlayerController')]=N(index=8,serial=2,address=1008)
  self.assertFalse(self.run_check())
 def test_restore_overlay_root_must_stay_bound_to_original_title(self):
  tree=N(index=7,serial=1,address=1007,class_name='WidgetTree');panel=N(index=8,serial=1,address=1008,class_name='Overlay')
  self.catalog.by_index.update({7:tree,8:panel});self.values[4].types[(0,'WidgetTree')]='ObjectProperty';self.values[4].values[(0,'WidgetTree')]=tree
  self.values[7]=N(types={(0,'RootWidget'):'ObjectProperty'},values={(0,'RootWidget'):panel},errors={},truncated=set())
  self.assertTrue(self.run_check(restore_tree=tree,restore_panel=panel))
  self.values[7].values[(0,'RootWidget')]=N(index=9,serial=1,address=1009,class_name='Overlay')
  self.assertFalse(self.run_check(restore_tree=tree,restore_panel=panel))
 def test_unreadable_link_is_not_retirement_proof(self):
  from expedition33.cinematics.original_game_action import NotReady
  self.values[1].errors[(0,'PlayerController')]='read failed'
  with self.assertRaisesRegex(NotReady,'unavailable'):self.run_check()
 def test_missing_or_wrong_schema_link_remains_strict(self):
  from expedition33.cinematics.original_game_action import NotReady
  for fields in ({},{(0,'PlayerController'):'IntProperty'}):
   self.values[1].types=fields
   with self.assertRaisesRegex(RuntimeError,'schema') as error:self.run_check()
   self.assertNotIsInstance(error.exception,NotReady)
 def test_destroyed_class_binding_and_null_link_do_not_keep_authority(self):
  self.player.object_flags=0x10;self.assertFalse(self.run_check(expected_reads=0))
  self.player.object_flags=0;self.values[1].values[(0,'PlayerController')]=None
  self.assertFalse(self.run_check())


class TitleInstallReaderTests(unittest.TestCase):
 def test_install_owns_shared_reader_and_resolver_borrows_without_new_worker(self):
  import io
  from unittest.mock import Mock
  from expedition33._reader import ReadBatch,active_reader
  import expedition33.title_menu as module
  process=N(stdin=io.StringIO(),stdout=io.StringIO(),wait=Mock(return_value=0))
  parent=N(pid=7,_session=N(_transport=N(pause_attachment_protocol=2,trace_renew_protocol=1)))
  entry=TitleMenuEntry(parent,N(),readiness=lambda:True)
  observed=[]
  def resolve(scope):
   owner=active_reader();self.assertTrue(owner._share)
   with ReadBatch(scope.pid) as child:
    self.assertIs(child._borrowed,owner);self.assertIs(active_reader(),owner)
    observed.append(owner)
   self.assertFalse(owner._closed)
   return None # Stop before UI construction; this test exercises real reader nesting.
  with patch('expedition33._reader.subprocess.Popen',return_value=process) as spawn,patch('expedition33._reader.threading.Thread'),patch.object(ReadBatch,'_line',return_value='{"event":"reader_ready","version":1,"pid":7}'),patch.object(module,'resolve_title',side_effect=resolve):
   self.assertFalse(entry.install())
  self.assertEqual(spawn.call_count,1);self.assertEqual(len(observed),1)
  self.assertTrue(observed[0]._closed);self.assertIsNone(active_reader())
  process.wait.assert_called_once()



class TitleInputRestorationTests(unittest.TestCase):
 def setUp(self):
  self.events=[];self.current=True
  parent=N(pid=7,_session=N(_transport=N()))
  self.menu=N(panel=N(state='built',menu=None,uncertain=False),failure=None)
  self.service=N(menu=self.menu,_failure=None)
  self.entry=TitleMenuEntry(parent,self.service,readiness=lambda:True)
  self.entry._title_restore_pending=True;self.entry._title_restore_disposition='pending'
  self.entry._active_call='active';self.entry._title_input='uionly';self.entry._button_focus='focus'
  self.entry._current_title=lambda:self.current
  self.entry.attachment=N(restore=lambda:self.events.append('overlay') or True)
  self.entry.invoke=lambda plan:True if plan=='active' else self.events.append(plan)
 def test_partial_authority_close_retains_presentation_as_known_pending(self):
  from expedition33.cinematics.original_game_action import NotReady
  self.entry._current_title=lambda:(_ for _ in ()).throw(NotReady('partial link'))
  with self.assertRaisesRegex(RuntimeError,'Title entry detach deferred'):self.entry.close()
  self.assertEqual(self.events,[]);self.assertTrue(self.entry._title_restore_pending)
  self.assertFalse(self.entry._title_restore_unknown)
 def test_partial_authority_poll_suppresses_work_without_closing(self):
  from expedition33.cinematics.original_game_action import NotReady
  self.entry._poll_title=lambda:(_ for _ in ()).throw(NotReady('partial link'))
  self.entry.poll();self.assertEqual(self.events,[]);self.assertTrue(self.entry._title_restore_pending)
 def test_acknowledged_hide_restores_overlay_then_uionly_then_button_focus(self):
  self.assertTrue(self.entry.restore_title_input_after_menu_close());self.assertEqual(self.events,['overlay','uionly','focus']);self.assertFalse(self.entry._title_restore_pending)
  self.assertTrue(self.entry.restore_title_input_after_menu_close());self.assertEqual(self.events,['overlay','uionly','focus'])
 def test_unknown_hide_never_restores_input(self):
  self.menu.panel.uncertain=True
  self.assertFalse(self.entry.restore_title_input_after_menu_close());self.assertEqual(self.events,[]);self.assertTrue(self.entry._title_restore_pending)
 def test_changed_context_retires_journal_without_mutating_new_world(self):
  self.current=False
  self.assertTrue(self.entry.restore_title_input_after_menu_close());self.assertEqual(self.events,[]);self.assertEqual(self.entry._title_restore_disposition,'context_retired')
 def test_unknown_input_restore_retains_journal_and_never_replays(self):
  def invoke(plan):
   if plan=='active':return True
   self.events.append(plan)
   if plan=='uionly':raise RuntimeError('unknown UIOnly acknowledgment')
  self.entry.invoke=invoke
  with self.assertRaisesRegex(RuntimeError,'unknown UIOnly'):self.entry.restore_title_input_after_menu_close()
  with self.assertRaisesRegex(RuntimeError,'without replay'):self.entry.restore_title_input_after_menu_close()
  self.assertEqual(self.events,['overlay','uionly']);self.assertTrue(self.entry._title_restore_pending)


class TitleCloseRestorationTests(TitleInputRestorationTests):
 def test_close_restores_title_before_releasing_entry_scope(self):
  self.entry.attachment.close=lambda:self.events.append('entry-detach') or True
  self.entry.scope=N(close=lambda:self.events.append('scope-close'))
  self.entry.close()
  self.assertEqual(self.events,['overlay','uionly','focus','entry-detach','scope-close'])
 def test_close_without_sdk_hide_ack_retains_entry(self):
  self.menu.panel.uncertain=True
  self.entry.attachment.close=lambda:(_ for _ in ()).throw(AssertionError('must retain'))
  with self.assertRaisesRegex(RuntimeError,'hide not acknowledged'):self.entry.close()
  self.assertTrue(self.entry._title_restore_pending);self.assertEqual(self.events,[])
if __name__=='__main__':unittest.main()
