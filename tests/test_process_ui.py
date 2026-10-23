import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch

from expedition33 import ui_shell_proof as proof, process_ui as m

def identity(n):return (7,n,3,0x10000+n*8)
def context(kind='title',world=1,gi=2,local=3,pc=4):
    return proof.UiContext(kind,identity(world),identity(gi),identity(local),identity(pc))

class ProcessUiTests(unittest.TestCase):
    def setUp(self):
        self.events=[];self.shells=[];self.entries=[];self.detach=True;self.entry_ack=True;self.shell_ack=True
        outer=self
        class Shell:
            def __init__(self,session,registry):
                self.service=object();self.ready=None;self.context=None;self.widgets=object();outer.shells.append(self);outer.events.append('shell.create')
            def prepare(self,ctx):self.context=ctx;outer.events.append('shell.build_and_prove');return True
            def detach(self):outer.events.append('menu.close.ack' if outer.detach else 'menu.close.pending');return outer.detach
            def rebind(self,ctx,*,preparing=False):
                outer.events.extend(('set_owner.'+ctx.kind,'getters.ack','plans.fresh','view.'+ctx.kind));self.context=ctx;return True
            def close(self):outer.events.append('shell.release.ack' if outer.shell_ack else 'shell.release.pending');return outer.shell_ack
            def poll(self):outer.events.append('shell.poll')
        class Entry:
            def __init__(self,session,service,ctx):
                self.ready=True;self.kind=ctx.kind;outer.entries.append(self);outer.events.append('entry.create.'+ctx.kind)
            def poll(self):outer.events.append('entry.poll.'+self.kind)
            def close(self):
                self.ready=False;outer.events.append('entry.restore.ack' if outer.entry_ack else 'entry.restore.pending');return outer.entry_ack
        self.session=N(_check=Mock());self.registry=object()
        self.router=m.ProcessUI(self.session,self.registry,shell_factory=Shell,entry_factory=Entry)
        self.title=context();self.world=context('world',world=5,pc=6)

    def test_verified_pre_title_context_warms_shell_without_entry_or_input(self):
        packet=N(ui_context=None,prewarm_context=self.title,title_ready=False)
        self.assertFalse(self.router.observe(packet))
        self.assertEqual(self.router.phase,'prewarmed');self.assertEqual(len(self.entries),0)
        self.assertEqual(self.events.count('shell.build_and_prove'),1)
        self.assertFalse(self.router.observe(packet))
        self.assertEqual(self.events.count('shell.build_and_prove'),1)
        self.assertTrue(self.router.observe(N(ui_context=self.title,title_ready=True)))
        self.assertEqual(len(self.entries),1)
        self.assertEqual(self.events.count('shell.build_and_prove'),1)

    def test_loading_world_rebinds_detached_shell_without_entry_or_repeating_proof(self):
        self.router.observe(N(ui_context=self.title,title_ready=True))
        packet=N(ui_context=None,prewarm_context=self.world,menu_ready=False)
        self.assertFalse(self.router.observe(packet))
        self.assertEqual(self.router.phase,'prewarmed')
        self.assertIsNone(self.router.entry)
        self.assertFalse(self.router.gameplay_ui_ready)
        self.assertFalse(self.router.observe(packet))
        self.assertEqual(self.events.count('set_owner.world'),1)
        self.assertTrue(self.router.observe(N(ui_context=self.world,menu_ready=True,
            admission=N(activation_ready=True))))
        self.assertEqual(self.events.count('set_owner.world'),1)

    def test_changed_pre_title_gi_requires_shell_release_before_rebuild(self):
        self.router.observe(N(ui_context=None,prewarm_context=self.title,title_ready=False))
        self.shell_ack=False
        changed=context(gi=9)
        self.assertFalse(self.router.observe(N(ui_context=None,prewarm_context=changed,title_ready=False)))
        self.assertEqual(len(self.shells),1);self.assertEqual(len(self.entries),0)
        self.shell_ack=True
        self.router.observe(N(ui_context=None,prewarm_context=changed,title_ready=False))
        self.assertEqual(len(self.shells),2);self.assertEqual(len(self.entries),0)

    def test_title_world_title_share_exact_tree_and_new_entries(self):
        self.assertTrue(self.router.poll(self.title));tree=self.router.shell.widgets
        self.assertTrue(self.router.poll(self.world));self.assertIs(tree,self.router.shell.widgets)
        self.assertTrue(self.router.poll(self.title));self.assertIs(tree,self.router.shell.widgets)
        self.assertEqual(len(self.shells),1);self.assertEqual(len(self.entries),3)
        self.assertEqual(self.events.count('shell.build_and_prove'),1)
        self.assertLess(self.events.index('menu.close.ack'),self.events.index('entry.restore.ack'))
        self.assertLess(self.events.index('entry.restore.ack'),self.events.index('set_owner.world'))
        self.assertLess(self.events.index('getters.ack'),self.events.index('entry.create.world'))
        self.assertFalse(self.entries[0].ready);self.assertFalse(self.entries[1].ready)

    def test_close_ack_barrier_blocks_setowner_and_new_entry(self):
        self.router.poll(self.title);self.detach=False
        self.assertFalse(self.router.poll(self.world));self.assertEqual(len(self.entries),1)
        self.assertNotIn('set_owner.world',self.events)
        self.detach=True;self.entry_ack=False
        self.assertFalse(self.router.poll(self.world));self.assertNotIn('set_owner.world',self.events)
        self.entry_ack=True;self.assertTrue(self.router.poll(self.world))
        self.assertEqual(self.events.count('set_owner.world'),1)

    def test_changed_gi_or_localplayer_requires_ack_retirement_then_rebuild(self):
        self.router.poll(self.title);old=self.router.shell.widgets
        self.shell_ack=False;changed=context('world',world=8,gi=9,local=10,pc=11)
        self.assertFalse(self.router.poll(changed));self.assertEqual(len(self.shells),1)
        self.shell_ack=True;self.assertTrue(self.router.poll(changed))
        self.assertEqual(len(self.shells),2);self.assertIsNot(self.router.shell.widgets,old)
        self.assertNotIn('set_owner.world',self.events)

    def test_uncertain_observation_retains_owners_and_no_new_mutations(self):
        self.router.poll(self.title);shell=self.router.shell;entry=self.router.entry;before=list(self.events)
        self.assertFalse(self.router.poll(None));self.assertIs(shell,self.router.shell);self.assertIs(entry,self.router.entry)
        self.assertEqual(self.events,before);self.assertIsNone(shell.ready);self.assertIsNone(entry.ready)
        self.router.poll(self.title);self.assertEqual(len(self.shells),1)

    def test_world_uncertainty_keeps_title_barrier_clear_without_tearing_down_entry(self):
        self.router.poll(self.world);entry=self.router.entry;before=list(self.events)
        self.assertTrue(self.router.title_cleanup_ready)
        self.assertFalse(self.router.poll(None))
        self.assertTrue(self.router.title_cleanup_ready)
        self.assertIs(self.router.entry,entry);self.assertEqual(self.events,before)
        self.assertIsNone(entry.ready)

    def test_retained_title_entry_still_blocks_world_until_close_ack(self):
        self.router.poll(self.title);self.entry_ack=False
        self.assertFalse(self.router.poll(self.world))
        self.assertFalse(self.router.title_cleanup_ready)
        self.assertFalse(self.router.poll(None));self.assertFalse(self.router.title_cleanup_ready)

    def test_combat_with_same_ui_context_does_not_retire_or_rebuild(self):
        self.router.poll(self.world);before=len(self.events)
        self.router.poll(self.world)
        self.assertEqual(self.events[before:],['entry.poll.world','shell.poll'])
        self.assertEqual(len(self.shells),1)

    def test_binding_growth_rebuild_is_detached_acknowledged_and_never_exposed_early(self):
        self.router.poll(self.title)
        self.router.shell.rebind=Mock(side_effect=m.UiCapacityRebuild('capacity'))
        self.shell_ack=False
        self.assertFalse(self.router.poll(self.world))
        self.assertIsNone(self.router.entry);self.assertEqual(len(self.entries),1)
        self.assertEqual(len(self.shells),1);self.assertFalse(self.router.failed)
        self.shell_ack=True
        self.assertFalse(self.router.poll(self.world));self.assertIsNone(self.router.shell)
        self.assertEqual(len(self.shells),1)
        self.assertTrue(self.router.poll(self.world));self.assertEqual(len(self.shells),2)
        self.assertEqual(len(self.entries),2)
        self.assertLess(self.events.index('shell.release.ack'),self.events.index('entry.create.world'))

    def test_packet_first_combat_cannot_admit_but_same_admitted_combat_keeps_shell(self):
        packet=N(ui_context=self.world,menu_ready=True,admission=N(activation_ready=False))
        self.assertFalse(self.router.observe(packet));self.assertEqual(self.shells,[])
        packet.admission.activation_ready=True;self.assertTrue(self.router.observe(packet))
        packet.admission.activation_ready=False;self.assertTrue(self.router.observe(packet))
        self.assertEqual(len(self.shells),1)

    def test_loaded_world_can_ack_old_title_entry_before_pause_shell_is_ready(self):
        self.router.poll(self.title);tree=self.router.shell.widgets
        packet=N(ui_context=self.world,menu_ready=False,admission=N(activation_ready=True))
        self.assertFalse(self.router.observe(packet))
        self.assertTrue(self.router.title_cleanup_ready)
        self.assertIsNone(self.router.entry);self.assertIs(self.router.shell.widgets,tree)
        self.assertNotIn('set_owner.world',self.events)
        packet.menu_ready=True;self.assertTrue(self.router.observe(packet))
        self.assertIs(self.router.shell.widgets,tree);self.assertEqual(len(self.shells),1)

    def test_title_packet_routes_after_world_without_changing_gameplay_registry(self):
        self.router.poll(self.world)
        packet=N(ui_context=self.title,title_ready=True)
        self.assertTrue(self.router.observe(packet));self.assertIs(self.router.registry,self.registry)
        self.assertEqual(self.router.context.kind,'title');self.assertEqual(len(self.shells),1)
        packet.title_ready=None;self.assertFalse(self.router.observe(packet));self.assertEqual(len(self.entries),2)

    def test_retained_frontend_preparation_failure_does_not_replay_or_kill_core(self):
        factory=self.router._shell_factory
        def create(*args):
            shell=factory(*args);shell.prepare=Mock(side_effect=m.UiFrontendHeld('retained'));return shell
        self.router._shell_factory=create
        self.assertFalse(self.router.poll(self.title));self.assertFalse(self.router.failed)
        self.assertEqual(self.router.phase,'frontend_held')
        self.assertFalse(self.router.poll(self.world));self.router.shell.prepare.assert_called_once()
        self.assertEqual(len(self.shells),1);self.assertEqual(len(self.entries),0)

    def test_pure_graph_preflight_rejection_holds_owner_without_core_failure_or_retry(self):
        factory=self.router._shell_factory
        def create(*args):
            shell=factory(*args);shell.prepare=Mock(side_effect=proof.UiProofPreflightRejected('capacity'));return shell
        self.router._shell_factory=create
        self.assertFalse(self.router.poll(self.title));self.assertFalse(self.router.failed)
        self.assertEqual(self.router.phase,'frontend_held')
        self.assertEqual(self.router.frontend_failed['outcome'],'held')
        self.assertFalse(self.router.poll(self.title));self.router.shell.prepare.assert_called_once()
        self.assertEqual(len(self.shells),1)

    def test_binding_growth_is_bounded_before_any_build_or_setter(self):
        shell=m.CachedProcessShell.__new__(m.CachedProcessShell)
        shell.registry=N(views=lambda:[{'keybinds':tuple(range(40))}])
        shell.service=N(menu=N(panel=N(key_row_capacity=32)))
        self.assertTrue(shell.needs_capacity_rebuild())
        shell.registry.views=lambda:[{'keybinds':tuple(range(129))}]
        with self.assertRaisesRegex(proof.UiProofMismatch,'supported fixed row bound'):
            shell.needs_capacity_rebuild()

    def test_unstable_identity_record_keeps_role_and_suspends_without_retry(self):
        from expedition33._metadata_stabilization import UnstableUIIdentity
        from expedition33.frontend_rejection import known_rejection
        service=N(menu=None)
        self.router.shell=N(service=service,scope=object(),journal=N(capture=Mock()))
        self.router._suspend_frontend(known_rejection(UnstableUIIdentity('object_patch')))
        self.assertFalse(self.router.failed)
        self.assertEqual(self.router.frontend_failed,dict(type='UnstableUIIdentity',native_error=0,
            outcome='not_dispatched',role='object_patch'))
        self.assertEqual(self.router.phase,'frontend_suspended')
        self.assertFalse(self.router.poll(self.world));self.assertEqual(len(self.entries),0)

    def test_unknown_handoff_failure_latches_owner_without_replay(self):
        self.router.poll(self.title);self.router.shell.rebind=Mock(side_effect=RuntimeError('unknown dispatch'))
        with self.assertRaisesRegex(RuntimeError,'unknown dispatch'):self.router.poll(self.world)
        self.assertTrue(self.router.failed)
        with self.assertRaisesRegex(RuntimeError,'retain owners'):self.router.poll(self.world)
        self.router.shell.rebind.assert_called_once_with(self.world)
        self.assertEqual(len(self.shells),1)

    def test_known_pending_proof_retains_shell_and_does_not_construct_entry(self):
        self.router.poll(self.title);self.router.shell.rebind=Mock(side_effect=proof.UiProofPending('getter release pending'))
        self.assertFalse(self.router.poll(self.world));self.assertEqual(self.router.phase,'proof_pending')
        self.assertFalse(self.router.failed);self.assertEqual(len(self.entries),1)

    def test_journal_requires_actual_released_not_target_exited(self):
        lease=N(_state='pending_release');child=N(_leases=[lease],_children=[])
        scope=N(_leases=[],_children=[child]);journal=m.LeaseJournal();journal.capture(scope)
        child._leases.clear();scope._children.clear()
        self.assertFalse(journal.acknowledged());lease._state='target_exited';self.assertFalse(journal.acknowledged())
        lease._state='released';self.assertTrue(journal.acknowledged())

    def test_first_prepare_pending_is_resumed_without_second_shell(self):
        factory=self.router._shell_factory
        def create(*args):
            shell=factory(*args);original=shell.prepare;shell.prepare=Mock(side_effect=[False,True]);return shell
        self.router._shell_factory=create
        self.assertFalse(self.router.poll(self.title));self.assertTrue(self.router.poll(self.title))
        self.assertEqual(len(self.shells),1);self.assertEqual(self.router.shell.prepare.call_count,2)

    def test_pending_entry_install_resumes_same_owner_without_rebind_or_reconstruction(self):
        factory=self.router._entry_factory
        def create(*args):
            entry=factory(*args);entry.poll=Mock(side_effect=[False,True]);return entry
        self.router._entry_factory=create
        self.assertFalse(self.router.poll(self.title));self.assertEqual(self.router.phase,'entry_pending')
        self.assertTrue(self.router.poll(self.title));self.assertEqual(len(self.entries),1)
        self.assertEqual(len(self.shells),1);self.assertNotIn('set_owner.title',self.events)

    def test_return_to_previous_context_during_pending_handoff_revalidates_instead_of_using_closed_entry(self):
        self.router.poll(self.title)
        original=self.router.shell.rebind
        self.router.shell.rebind=Mock(side_effect=proof.UiProofPending('not yet'))
        self.assertFalse(self.router.poll(self.world));self.assertIsNone(self.router.entry)
        self.router.shell.rebind=original
        self.assertTrue(self.router.poll(self.title));self.assertEqual(len(self.entries),2)
        self.assertIn('set_owner.title',self.events)

class InitialPreparedPlanTests(unittest.TestCase):
    def test_proof_invalidated_plan_is_reprimed_inside_reader_before_ready(self):
        from contextlib import contextmanager
        from expedition33 import _reader
        events=[];session=N(_menu_plan_cache=object())
        shell=m.CachedProcessShell.__new__(m.CachedProcessShell)
        shell.scope=N(pid=7);shell.context=None;shell.needs_capacity_rebuild=Mock()
        shell._factory=lambda kind:object
        panel=N(state='built',catalog=N(objects=()),_planner=N(_catalog=N(objects=())))
        def verify(*args):
            events.append('proof');session._menu_plan_cache=None
        def prime():
            self.assertIsNone(shell.context)
            self.assertIsNone(session._menu_plan_cache)
            events.append('prime');session._menu_plan_cache=object()
        panel.prime_menu_plan=prime
        shell.proof=N(verify=verify)
        shell.service=N(_view_options={},_failure=None,menu=N(panel=panel),
            prepare=lambda:events.append('prepare'))
        @contextmanager
        def batch(pid,**options):
            self.assertEqual(pid,7);events.append('reader.enter')
            yield
            events.append('reader.exit')
        ctx=context()
        with patch.object(_reader,'ReadBatch',side_effect=batch):
            self.assertTrue(shell.prepare(ctx))
        self.assertEqual(events,['prepare','reader.enter','proof','prime','reader.exit'])
        self.assertIs(shell.context,ctx);self.assertIsNotNone(session._menu_plan_cache)

    def test_proof_and_prime_share_one_read_only_worker(self):
        from expedition33 import _reader
        events=[]
        shell=m.CachedProcessShell.__new__(m.CachedProcessShell)
        shell.scope=N(pid=7);shell.context=None;shell.needs_capacity_rebuild=Mock()
        shell._factory=lambda kind:object
        def verify(*args):
            with _reader.ReadBatch(7):events.append('proof')
        def prime():
            self.assertIsNotNone(_reader.active_reader());events.append('prime')
        shell.proof=N(verify=verify)
        shell.service=N(_view_options={},_failure=None,
            menu=N(panel=N(state='built',prime_menu_plan=prime,catalog=N(objects=()),_planner=N(_catalog=N(objects=())))),prepare=Mock())
        # Exercise real ContextVar/nesting ownership. Only child-process IO is
        # mocked; an outer nonsharing reader around proof would fail here.
        with patch.object(_reader.subprocess,'Popen',return_value=Mock()) as spawn, \
                patch.object(_reader.ReadBatch,'_read'), \
                patch.object(_reader.ReadBatch,'_line',return_value='{"event":"reader_ready","version":1,"pid":7}'):
            self.assertTrue(shell.prepare(context()))
        spawn.assert_called_once()
        self.assertEqual(events,['proof','prime']);self.assertIsNone(_reader.active_reader())

    def test_prime_failure_does_not_publish_context(self):
        from contextlib import nullcontext
        from expedition33 import _reader
        shell=m.CachedProcessShell.__new__(m.CachedProcessShell)
        shell.scope=N(pid=7);shell.context=None;shell.needs_capacity_rebuild=Mock()
        shell._factory=lambda kind:object;shell.proof=N(verify=Mock())
        panel=N(state='built',prime_menu_plan=Mock(side_effect=RuntimeError('plan failed')),catalog=N(objects=()),_planner=N(_catalog=N(objects=())))
        shell.service=N(_view_options={},_failure=None,menu=N(panel=panel),prepare=Mock())
        with patch.object(_reader,'ReadBatch',return_value=nullcontext()):
            with self.assertRaisesRegex(RuntimeError,'plan failed'):shell.prepare(context())
        self.assertIsNone(shell.context)

class ProofGetterTests(unittest.TestCase):
    def test_loading_metadata_uses_final_owned_graph_not_initial_discovery(self):
        from expedition33 import _metadata_stabilization as metadata,_stable_lease as stable
        row=N(serial=0,class_name='Class');unrelated=N(class_name='BlueprintGeneratedClass')
        anchors=N(serial=0,class_name='ScriptStruct')
        pruned=object();final=N(objects=(row,unrelated,anchors),subset=Mock(return_value=pruned));fresh=object()
        owner=N(prepare=Mock(return_value=N(by_index={1:row})))
        session=N(_menu_plan_cache=object(),_menu_schema_observations=Mock())
        owned=object();scope=N(_session=session,invocation_planner=Mock(return_value=N()),_leases=[N(active=True,object=owned)])
        planner=N(_catalog=final,close=Mock())
        panel=N(catalog=object(),_planner=planner,scope=scope,_functions={'old':1},_defaults={'old':1},
            widget=owned,tree=owned,canvas=owned,player=object())
        def admit(catalog,obj):
            if obj is unrelated or obj is anchors:raise ValueError('outside native metadata whitelist')
            return obj
        with patch.object(metadata,'script_function',side_effect=admit), \
             patch.object(metadata,'process_preparation',return_value=owner), \
             patch.object(stable,'fresh_catalog_replacing',return_value=fresh) as recapture:
            proof.prepare_panel_metadata(panel)
        owner.prepare.assert_called_once_with(pruned,[row])
        recapture.assert_called_once_with(pruned,(row,))
        self.assertIn(owned,final.subset.call_args.args[0]);self.assertNotIn(unrelated,final.subset.call_args.args[0])
        self.assertIn(anchors,final.subset.call_args.args[0])
        self.assertIs(panel.catalog,fresh);self.assertFalse(panel._functions);self.assertFalse(panel._defaults)
        planner.close.assert_called_once();session._menu_schema_observations.clear.assert_called_once()

    def test_loading_context_null_and_serial_races_defer_without_hiding_programming_errors(self):
        p=proof.OwnedUiProof(N())
        for error in (RuntimeError('Current history context reference is null'),
                proof.RuntimeQueryError('DESCRIPTOR_IDENTITY_CHANGED')):
            p._current_observation=Mock(side_effect=error)
            with self.assertRaises(proof.UiProofPending):p._current(context('world'),preparing=True)
        p._current_observation=Mock(side_effect=RuntimeError('programming failure'))
        with self.assertRaisesRegex(RuntimeError,'programming failure'):p._current(context('world'))

    def test_metadata_discovery_uses_bounded_cdo_names_and_defers_unavailable_reads(self):
        first=obj(1849,'GameInstance','Class');second=obj(1850,'LocalPlayer','Class')
        first.serial=second.serial=0
        catalog=N(by_index={1849:first,1850:second})
        catalog.with_observations=lambda other:catalog
        def discover(pid,*,names):
            self.assertEqual(names,('Default__GameInstance','Default__LocalPlayer'))
            return catalog
        with patch.object(proof,'capture_matching',side_effect=discover) as query:
            self.assertEqual(proof.refresh_panel_metadata(7,[first,second]),(first,second))
            self.assertEqual(query.call_count,1)
        with patch.object(proof,'capture_matching',side_effect=proof.RuntimeQueryError('READ_FAILED')):
            with self.assertRaises(proof.UiProofPending):proof.refresh_panel_metadata(7,[first])

    def test_context_refresh_rediscovers_zero_metadata_and_preserves_positive_selectors(self):
        old=obj(1849,'GameInstance','Class');old.serial=0
        current=obj(1849,'GameInstance','Class');current.serial=77
        with patch.object(proof,'capture_matching',return_value=N(by_index={1849:current})) as discover:
            self.assertEqual(proof.refresh_panel_metadata(7,[old]),(current,))
            discover.assert_called_once_with(7,names=('Default__GameInstance',))
            old.serial=76
            self.assertEqual(proof.refresh_panel_metadata(7,[old]),(old,))
            self.assertEqual(discover.call_count,1)
    def test_reference_identity_ignores_observed_gc_flags_but_rejects_recycling(self):
        first=N(pid=7,index=10,serial=4,address=100,object_flags=0)
        current=N(pid=7,index=10,serial=4,address=100,object_flags=0x80000000)
        self.assertTrue(proof.same_identity(first,current))
        current.serial=5;self.assertFalse(proof.same_identity(first,current))
        self.assertFalse(proof.same_identity(None,first))
    def test_selected_metadata_refresh_avoids_scan_and_rejects_recycled_class(self):
        old=obj(1849,'GameInstance','Class');old.serial=0
        current=obj(1849,'GameInstance','Class');current.serial=77
        with patch.object(proof,'capture_matching') as scan:
            self.assertEqual(proof.refresh_panel_metadata(7,[old],observed=N(by_index={old.index:current})),(current,))
            current.address+=16
            with self.assertRaises(proof.UiProofPending):
                proof.refresh_panel_metadata(7,[old],observed=N(by_index={old.index:current}))
        scan.assert_not_called()
    def test_zero_localplayer_constraint_uses_real_script_provenance_preparation(self):
        from expedition33 import _metadata_stabilization as metadata,_stable_lease as stable
        engine=N(index=100,class_name='Package',outer_index=-1,serial=1)
        umg=N(index=101,class_name='Package',outer_index=-1,serial=1)
        classes=[N(pid=7,index=1916+i,name=name,class_name='Class',serial=0 if i==0 else 8,
            address=0x10000+i*16,outer_index=100 if i<2 else 101,object_flags=0)
            for i,name in enumerate(('LocalPlayer','PlayerController','Widget','UserWidget'))]
        def catalog(serial):
            rows=[N(**vars(o)) for o in classes];rows[0].serial=serial
            by_index={o.index:o for o in (*rows,engine,umg)}
            def path(obj):
                if obj.index in (100,101):return '/Script/Engine' if obj.index==100 else '/Script/UMG'
                return ('/Script/Engine.' if obj.outer_index==100 else '/Script/UMG.')+obj.name
            result=N(objects=tuple(rows),by_index=by_index,resolve=lambda obj:by_index[obj.index],
                path_name=path,find_path=lambda name,kind:next(o for o in rows if path(o)==name))
            result.with_observations=lambda observed:result
            return result
        before=catalog(0);after=catalog(4001);selected=[]
        def prepare(current,rows):
            for row in rows:
                self.assertIs(metadata.script_function(current,row),row)
                selected.append(row.index)
            return after
        session=N(_check=Mock(),_transport=N(metadata_stabilization_protocol=1),_menu_plan_cache=object())
        p=proof.OwnedUiProof(N(pid=7,_session=session))
        with patch.object(proof,'capture_matching',side_effect=(before,after)) as capture, \
                patch.object(metadata,'process_preparation',return_value=N(prepare=prepare)), \
                patch.object(stable,'fresh_catalog_replacing',return_value=after) as replace:
            fresh=p._functions(before)
        self.assertEqual(selected,[1916]);self.assertEqual(capture.call_count,2)
        self.assertIn('Default__LocalPlayer',capture.call_args.kwargs['names'])
        self.assertEqual(fresh.find_path('/Script/Engine.LocalPlayer','Class').serial,4001)
        replace.assert_called_once_with(before,after.objects)
        plan=N(target=N(serial=1),function=N(serial=1),objects=(),parameters=(N(constraint=classes[0]),))
        with self.assertRaises(metadata.UnstableUIIdentity):metadata.require_positive_plan_identities(plan)
        plan.parameters=(N(constraint=fresh.find_path('/Script/Engine.LocalPlayer','Class')),)
        self.assertIs(metadata.require_positive_plan_identities(plan),plan)
        with patch.object(proof,'capture_selected',return_value=after) as selected_read, \
                patch.object(proof,'capture_matching') as global_scan, \
                patch.object(stable,'fresh_catalog_replacing',return_value=after):
            self.assertIs(p._functions(after),after)
        selected_read.assert_called_once_with(7,session._ui_proof_metadata_selectors)
        global_scan.assert_not_called()

    def test_proof_function_metadata_is_stabilized_then_fully_recaptured(self):
        from expedition33 import _metadata_stabilization as metadata,_stable_lease as stable
        old=N(objects=());extra=N(objects=(),by_index={},find_path=lambda *_:N(serial=1001));fresh=N(objects=())
        scope=N(pid=7,_session=N(_transport=N(metadata_stabilization_protocol=1)))
        p=proof.OwnedUiProof(scope)
        with patch.object(metadata,'prepare_discovery',return_value=(extra,())) as prepare, \
                patch.object(stable,'fresh_catalog_replacing',return_value=fresh) as recapture:
            self.assertIs(p._functions(old),fresh)
            self.assertIs(prepare.call_args.args[0],scope._session)
            recapture.assert_called_once_with(old,extra.objects)

    def test_missing_positive_metadata_protocol_rejects_before_any_proof_dispatch(self):
        p=proof.OwnedUiProof(N(pid=7,_session=N(_transport=object())))
        with self.assertRaisesRegex(proof.UiProofMismatch,'positive metadata'):p._functions(object())

    def test_getter_result_lease_ack_required_and_journal_retained(self):
        lease=N(_state='pending_release')
        result=N(return_value='expected',release=Mock(return_value=False),_leases=[lease])
        planner=N(prepare=Mock(return_value=N(invoke=Mock(return_value=result))),close=Mock(),_metadata=N(_entries={}))
        scope=N(invocation_planner=Mock(return_value=planner))
        p=proof.OwnedUiProof(scope)
        fn=N(class_name='Function',outer_index=4,name='GetOwningPlayer')
        catalog=N(find_class=lambda owner:N(index=4),objects=[fn])
        with self.assertRaises(proof.UiProofPending):p._invoke(catalog,object(),'Widget','GetOwningPlayer')
        self.assertEqual(p.pending_results,[result]);self.assertTrue(p.pending())
        self.assertIs(planner._require_stable_ui_identities,True)
        lease._state='released';self.assertFalse(p.pending());planner.close.assert_called_once_with()

    def test_released_getter_result_never_remains_owned(self):
        result=N(return_value='expected',release=Mock(return_value=True),_leases=[])
        planner=N(prepare=Mock(return_value=N(invoke=Mock(return_value=result))),close=Mock(),_metadata=N(_entries={}))
        p=proof.OwnedUiProof(N(invocation_planner=lambda **kw:planner))
        catalog=N(find_class=lambda owner:N(index=4),objects=[N(class_name='Function',outer_index=4,name='GetOwningPlayer')])
        self.assertEqual(p._invoke(catalog,object(),'Widget','GetOwningPlayer'),'expected')
        self.assertEqual(p.pending_results,[])


class RebindPreparedFrameTests(unittest.TestCase):
    def setUp(self):
        from contextlib import contextmanager
        from expedition33 import _reader
        self.reader_active=False
        @contextmanager
        def batch(pid,**options):
            self.reader_active=True
            try:yield
            finally:self.reader_active=False
        stub=patch.object(_reader,'ReadBatch',side_effect=batch)
        stub.start();self.addCleanup(stub.stop)

    def shell(self,*,failure=None):
        events=[]
        def paint():
            self.assertTrue(self.reader_active)
            events.append('paint')
            if failure is not None:raise failure
        registry=N(views=lambda:[]);menu=N(panel=N(state='built',menu=None,key_row_capacity=32),
            view=Mock(),actions=[],_render_view=Mock(return_value=object()),_paint=paint,
            prepared_view_state=Mock(return_value=('world','prepared')))
        service=N(menu=menu,_view_options={},_observed='old',_prepared_view_state='old',
            _snapshot=Mock(side_effect=lambda:events.append('snapshot') or 'fresh'))
        shell=m.CachedProcessShell.__new__(m.CachedProcessShell)
        shell.registry=registry;shell.service=service;shell.proof=N(verify=Mock())
        shell.scope=N(pid=7)
        shell._factory=Mock(return_value=lambda registry:Mock())
        return shell,menu,service,events

    def test_rebind_records_prepared_markers_only_after_successful_detached_paint(self):
        shell,menu,service,events=self.shell()
        self.assertTrue(shell.rebind(context('world')))
        self.assertEqual(events,['paint','snapshot'])
        self.assertEqual(service._observed,'fresh')
        self.assertEqual(service._prepared_view_state,('world','prepared'))
        menu.prepared_view_state.assert_called_once_with()

    def test_failed_detached_paint_does_not_publish_reusable_frame(self):
        shell,menu,service,events=self.shell(failure=ValueError('paint failure'))
        with self.assertRaises(ValueError):shell.rebind(context('world'))
        self.assertEqual(events,['paint']);service._snapshot.assert_not_called()
        self.assertIsNone(service._observed);self.assertIsNone(service._prepared_view_state)


def obj(index,name,cls='Widget',outer=-1,class_index=102):
    return N(pid=7,index=index,serial=3,address=0x10000+index*8,name=name,class_name=cls,
        object_flags=0,outer_index=outer,outer_serial=3 if outer>=0 else 0,class_index=class_index)


class GraphProofTests(unittest.TestCase):
    def setUp(self):
        from expedition33.mods_workspace_scroll import ScrollWorkspacePanel
        self.ctx=context();self.gi=obj(2,'GI','BP_jRPG_GI_Custom_C')
        self.root=obj(20,'Root','CommonActivatableWidget',2,100)
        self.tree=obj(21,'Tree','WidgetTree',20,101);self.canvas=obj(22,'Canvas','CanvasPanel',21)
        self.rows={o.index:o for o in (self.gi,self.root,self.tree,self.canvas,
            obj(99,'UserWidget','Class'),obj(101,'WidgetTree','Class'))}
        outer=self
        class Catalog:
            def resolve(self,value):return outer.rows[value.index]
            def find_class(self,name):return N(index=99)
            @property
            def by_index(self):return outer.rows
            def ancestors(self,index):return (99,) if index==100 else ()
            def outer_chain(self,value):
                result=[]
                while True:
                    result.append(value)
                    if value.outer_index<0:return tuple(reversed(result))
                    value=outer.rows[value.outer_index]
            def with_observations(self,other):return self
        self.catalog=Catalog()
        self.scope=N(pid=7,_leases=[N(active=True,object=o) for o in (self.root,self.tree,self.canvas)])
        self.panel=ScrollWorkspacePanel.__new__(ScrollWorkspacePanel)
        self.panel.scope=self.scope;self.panel.state='built';self.panel.menu=None;self.panel.uncertain=False
        self.panel.widget=self.root;self.panel.tree=self.tree;self.panel.canvas=self.canvas
        self.proof=proof.OwnedUiProof(self.scope)

    def graph(self,root_widget=None):
        def reference(cat,target,owner,name,**kwargs):
            return (self.tree if name=='WidgetTree' else root_widget or self.canvas),cat
        with patch.object(proof,'capture_selected',return_value=self.catalog), \
                patch.object(proof,'read_object_reference',side_effect=reference):
            return self.proof._graph(self.panel,self.ctx,self.catalog)

    def test_exact_owned_scroll_tree_outer_gi_and_property_readbacks(self):
        self.assertIs(self.graph(),self.catalog)

    def test_large_production_tree_has_complete_bounded_two_pass_coverage(self):
        extras=[obj(200+i,'Child'+str(i),'CanvasPanelSlot',21) for i in range(1300)]
        self.rows.update({o.index:o for o in extras})
        self.scope._leases.extend(N(active=True,object=o) for o in extras)
        def reference(cat,target,owner,name,**kwargs):
            return (self.tree if name=='WidgetTree' else self.canvas),cat
        with patch.object(proof,'capture_selected',return_value=self.catalog) as capture, \
                patch.object(proof,'read_object_reference',side_effect=reference):
            self.assertIs(self.proof._graph(self.panel,self.ctx,self.catalog),self.catalog)
        calls=[call.args[1] for call in capture.call_args_list]
        self.assertEqual(len(calls),4);self.assertTrue(all(len(chunk)<=1024 for chunk in calls))
        expected={proof.identity(o)[1:] for o in (*extras,self.root,self.tree,self.canvas)}
        self.assertEqual(set(calls[0]+calls[1]),expected)
        self.assertEqual(set(calls[2]+calls[3]),expected)

    def test_topology_change_between_complete_passes_is_pending_not_ready(self):
        reads=[0]
        def observe(*args):
            reads[0]+=1
            if reads[0]==2:self.canvas.outer_index=20
            return self.catalog
        with patch.object(proof,'capture_complete',side_effect=observe):
            with self.assertRaisesRegex(proof.UiProofPending,'graph changed'):
                self.proof._graph(self.panel,self.ctx,self.catalog)

    def test_complete_capture_missing_late_object_does_not_drop_coverage(self):
        selectors=((20,3,self.root.address),(888,3,0x99999))
        with patch.object(proof,'capture_selected',return_value=self.catalog):
            with self.assertRaisesRegex(proof.UiProofPending,'incomplete or changed'):
                proof.capture_complete(7,selectors)

    def test_complete_capture_hard_bound_rejects_before_read(self):
        with patch.object(proof,'capture_selected') as capture:
            with self.assertRaises(proof.UiProofPreflightRejected):
                proof.capture_complete(7,tuple((n,1,n+1) for n in range(8193)))
            capture.assert_not_called()

    def test_complete_capture_known_read_race_is_pending_without_retry(self):
        from expedition33 import RuntimeQueryError
        with patch.object(proof,'capture_selected',side_effect=RuntimeQueryError('SELECTED_DEPENDENCY_CHANGED')) as capture:
            with self.assertRaises(proof.UiProofPending):
                proof.capture_complete(7,((20,3,self.root.address),))
            self.assertEqual(capture.call_count,1)

    def test_world_outer_or_nested_userwidget_rejects_before_rebinding(self):
        self.root.outer_index=1
        with self.assertRaisesRegex(proof.UiProofMismatch,'game instance'):self.graph()
        self.root.outer_index=2
        nested=obj(23,'Nested','UserWidget',21,100)
        self.rows[23]=nested;self.scope._leases.append(N(active=True,object=nested))
        with self.assertRaisesRegex(proof.UiProofMismatch,'Nested UserWidgets'):self.graph()

    def test_changed_root_property_or_active_native_menu_rejects(self):
        with self.assertRaisesRegex(proof.UiProofMismatch,'property readback'):
            self.graph(root_widget=obj(24,'OtherRoot'))
        self.panel.menu=object()
        with self.assertRaises(proof.UiProofPending):self.graph()


class TypedReadbackTests(unittest.TestCase):
    def setUp(self):
        self.ctx=context();self.pc=obj(4,'PC','PlayerController');self.local=obj(3,'LP','LocalPlayer')
        self.root=obj(20,'Root','CommonActivatableWidget');self.library=obj(30,'Default__GameplayStatics','GameplayStatics')
        self.catalog=N(resolve=lambda value:value,select=lambda name:(self.library,),by_index={4:self.pc})
        self.catalog.with_observations=lambda observed:self.catalog
        self.scope=N(pid=7,_session=N(_menu_plan_cache=object()),invocation_planner=Mock(return_value=Mock()))
        self.p=proof.OwnedUiProof(self.scope)
        self.p._current=Mock(return_value=(self.catalog,self.pc));self.p._graph=Mock(return_value=self.catalog)
        self.p._functions=Mock(return_value=self.catalog)
        self.panel=N(widget=self.root,catalog=N(objects=[]),scope=N(_leases=[],invocation_planner=self.scope.invocation_planner),
            _planner=Mock(),prime_menu_plan=Mock(),_functions={},_defaults={})

    def verify(self,**options):
        from contextlib import nullcontext
        with patch.object(proof,'ReadBatch',side_effect=lambda pid:nullcontext()), \
                patch.object(proof,'capture_selected',return_value=self.catalog):
            return self.p.verify(self.panel,self.ctx,**options)

    def test_all_three_typed_readbacks_match_current_context(self):
        self.p._invoke=Mock(side_effect=(self.pc,self.local,self.pc))
        self.assertTrue(self.verify())
        names=[call.args[3] for call in self.p._invoke.call_args_list]
        self.assertEqual(names,['GetOwningPlayer','GetOwningLocalPlayer','GetPlayerController'])
        self.assertEqual(self.p._invoke.call_args.kwargs,dict(WorldContextObject=self.root,PlayerIndex=0))
        self.assertEqual(self.p._current.call_count,2)

    def test_old_world_controller_readback_rejects_even_if_player_and_lp_match(self):
        self.p._invoke=Mock(side_effect=(self.pc,self.local,obj(8,'OldPC','PlayerController')))
        with self.assertRaisesRegex(proof.UiProofMismatch,'world readback'):self.verify()

    def test_setter_not_replayed_after_known_getter_lease_deferral(self):
        calls=[];first=[True]
        def invoke(cat,target,owner,name,**args):
            calls.append((name,args))
            if name=='SetOwningPlayer':return None
            if name=='GetOwningPlayer' and first[0]:
                first[0]=False;raise proof.UiProofPending('getter release pending')
            return self.local if name=='GetOwningLocalPlayer' else self.pc
        self.p._invoke=invoke
        with self.assertRaises(proof.UiProofPending):self.verify(rebind=True)
        self.assertTrue(self.verify(rebind=True))
        self.assertEqual(sum(name=='SetOwningPlayer' for name,args in calls),1)
        self.assertEqual(calls[0][1],dict(LocalPlayerController=self.pc))
        self.assertIsNone(self.scope._session._menu_plan_cache)
        self.panel.prime_menu_plan.assert_called_once_with()

    def test_loading_argument_rejection_holds_old_context_without_dispatch_replay(self):
        from expedition33.invocation import InvocationError
        self.p._invoke=Mock(side_effect=InvocationError('retired argument',outcome='not_dispatched',native_error=218))
        with self.assertRaises(proof.UiProofPending):self.verify(rebind=True,preparing=True)
        with self.assertRaises(proof.UiProofPending):self.verify(rebind=True,preparing=True)
        self.assertEqual(self.p._invoke.call_count,1)
        self.ctx=context('world',world=9,pc=8);current=obj(8,'PC','PlayerController')
        self.catalog.by_index[current.index]=current;self.p._current.return_value=(self.catalog,current)
        self.p._invoke.side_effect=(None,current,self.local,current)
        self.assertTrue(self.verify(rebind=True,preparing=True))
        self.assertEqual(self.p._invoke.call_count,5)

    def test_unknown_dispatch_outcome_is_never_treated_as_loading_deferral(self):
        from expedition33.invocation import InvocationError
        self.p._invoke=Mock(side_effect=InvocationError('unknown',outcome='unknown',native_error=218))
        with self.assertRaises(InvocationError):self.verify(rebind=True)

if __name__=='__main__':unittest.main()
