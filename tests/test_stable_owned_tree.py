import unittest
from contextlib import nullcontext
from types import SimpleNamespace as NS
from expedition33 import _stable_lease as stable, _lease_wire as wire
from expedition33.ownership import ObjectLease,LeaseError

class Catalog:
    def __init__(self,*objects):self.by_index={o.index:o for o in objects};self.objects=objects;self.pid=1
    def resolve(self,obj):
        value=self.by_index[obj.index]
        if (value.serial,value.address)!=(obj.serial,obj.address):raise ValueError('stale identity')
        return value

class Session:
    def __init__(self):
        self.pid=1;self._leases=set();self._closed=False;self.aborted=False
        self._transport=NS(stable_lease_protocol=1,lease_limit=8192,_closed=False)
    def _check(self):pass
    def _abort_ownership(self):self.aborted=True
class Scope:
    def __init__(self,session):self._session=session;self._closed=False;self._leases=[]
    def _check(self):pass
    def _lease_context(self):return nullcontext()
def obj(index,serial,kind='WidgetTree',outer=1):
    return NS(pid=1,index=index,serial=serial,address=0x10000+index*16,class_name=kind,outer_index=outer)
def ack(sent,*,serial=1001,error=0,outcome=1,token=19):
    old=wire.PACKET.unpack(sent)
    return wire.PACKET.pack(1,error,outcome,2,old[4],serial,old[6],token).hex()

class StableLeaseTests(unittest.TestCase):
    def test_cross_process_acquisition_is_rejected_before_transport(self):
        session=Session();scope=Scope(session);foreign=obj(2,0);foreign.pid=2
        session._transport.command=lambda *a:self.fail('cross-process dispatch')
        with self.assertRaises(ValueError):stable.acquire_stable(scope,foreign)
        self.assertFalse(session.aborted);self.assertEqual(session._leases,set())

    def setup_case(self):
        session=Session();scope=Scope(session);parent=obj(1,10,'CommonActivatableWidget',0)
        tree=obj(2,0);owner=obj(3,11,'Class',0);fresh_tree=obj(2,1001)
        old=Catalog(parent,tree,owner);fresh=Catalog(parent,fresh_tree,owner)
        lease=ObjectLease(session,5,parent);session._leases.add(lease);scope._leases.append(lease)
        session._transport.command=lambda command,sent:{'lease_packet':ack(sent)}
        return session,scope,parent,tree,owner,old,fresh
    def test_wire_preserves_index_address_positive_serial_and_rejects_false_success(self):
        sent=wire.request('lease-acquire',object=obj(2,0))
        self.assertEqual(stable.decode(sent,ack(sent),capacity=8192)['identity'],(2,1001,0x10020))
        for packet in (ack(sent,serial=0),ack(sent,token=0),ack(sent,serial=99)):
            with self.assertRaises(ValueError):stable.decode(sent,packet,capacity=8192)
        positive=wire.request('lease-acquire',object=obj(2,1002))
        with self.assertRaises(ValueError):stable.decode(positive,ack(positive,serial=1003),capacity=8192)
    def test_adopts_token_before_fresh_read_and_returns_only_fresh_catalog(self):
        session,scope,parent,tree,owner,old,fresh=self.setup_case();reads=[]
        def capture(pid,selectors):
            self.assertEqual(len(session._leases),2);self.assertEqual(scope._leases[-1]._token,19)
            self.assertIsNone(scope._leases[-1]._object)
            self.assertEqual(selectors[0],(tree.index,1001,tree.address));return fresh
        def reference(catalog,*args,**kwargs):
            reads.append(catalog);return catalog.by_index[2],catalog
        current,selected=stable.stabilize_owned_tree(scope,old,parent,tree,owner,read_reference=reference,capture=capture)
        self.assertIs(selected,fresh);self.assertIs(current,fresh.by_index[2]);self.assertEqual(reads,[old,fresh])
        self.assertIs(scope._leases[-1].object,current);self.assertFalse(session.aborted)
    def test_unowned_parent_or_changed_before_property_never_acquires(self):
        session,scope,parent,tree,owner,old,fresh=self.setup_case();scope._leases=[]
        session._transport.command=lambda *args:self.fail('must not acquire')
        with self.assertRaises(LeaseError):stable.stabilize_owned_tree(scope,old,parent,tree,owner)
        session,scope,parent,tree,owner,old,fresh=self.setup_case()
        session._transport.command=lambda *args:self.fail('must not acquire')
        with self.assertRaises(Exception):stable.stabilize_owned_tree(scope,old,parent,tree,owner,read_reference=lambda *a,**k:(None,old))
    def test_changed_after_property_retains_adopted_lease_without_replay(self):
        session,scope,parent,tree,owner,old,fresh=self.setup_case();calls=[]
        session._transport.command=lambda command,sent:(calls.append(command) or {'lease_packet':ack(sent)})
        def reference(catalog,*a,**k):return (tree,old) if catalog is old else (None,fresh)
        with self.assertRaises(Exception):stable.stabilize_owned_tree(scope,old,parent,tree,owner,read_reference=reference,capture=lambda *a:fresh)
        self.assertEqual(calls,['stable-lease-acquire']);self.assertEqual(scope._leases[-1]._token,19)
        self.assertTrue(scope._leases[-1].active);self.assertFalse(session.aborted)
    def test_unknown_ack_adopts_known_token_then_aborts_without_reader(self):
        session,scope,parent,tree,owner,old,fresh=self.setup_case()
        session._transport.command=lambda command,sent:{'lease_packet':ack(sent,error=413,outcome=2,serial=0)}
        with self.assertRaises(LeaseError):stable.stabilize_owned_tree(scope,old,parent,tree,owner,read_reference=lambda *a,**k:(tree,old),capture=lambda *a:self.fail('unknown read'))
        self.assertEqual(scope._leases[-1]._token,19);self.assertTrue(session.aborted)

    def test_tokenless_quarantine_aborts_without_read_or_replay(self):
        session,scope,parent,tree,owner,old,fresh=self.setup_case();calls=[]
        session._transport.command=lambda command,sent:(calls.append(command) or {'lease_packet':ack(sent,error=408,outcome=2,serial=0,token=0)})
        with self.assertRaises(LeaseError):stable.stabilize_owned_tree(scope,old,parent,tree,owner,read_reference=lambda *a,**k:(tree,old),capture=lambda *a:self.fail('unknown read'))
        self.assertTrue(session.aborted);self.assertEqual(calls,['stable-lease-acquire']);self.assertEqual(len(scope._leases),1)

    def test_rediscovery_excludes_root_and_never_merges_old_child_catalog(self):
        parent=obj(1,10,'CommonActivatableWidget',0);tree=obj(2,1001);owner=obj(3,11,'Class',0)
        static=Catalog(owner);root=Catalog(parent,owner);full=Catalog(parent,tree,owner)
        merges=[]
        def merge(observed):
            self.assertIs(observed,root);self.assertNotIn(tree.index,static.by_index)
            merges.append(observed);return Catalog(parent,owner)
        static.with_observations=merge
        def read(catalog,target,cls,*a,**k):
            self.assertIs(catalog.resolve(target),parent);self.assertIs(cls,owner)
            return tree,full
        catalog,current,selected=stable.rediscover_owned_tree(1,lambda:static,parent,tree,owner.index,capture=lambda *a:root,read_reference=read)
        self.assertIs(current,tree);self.assertIs(selected,full);self.assertEqual(merges,[root])
        with self.assertRaises(Exception):stable.rediscover_owned_tree(1,lambda:static,parent,tree,owner.index,capture=lambda *a:root,read_reference=lambda *a,**k:(obj(2,1002),full))

    def test_owned_metadata_refresh_recaptures_only_selected_identities_and_validates_context(self):
        parent=obj(1,10,'CommonActivatableWidget',0);tree=obj(2,1001);owner=obj(3,11,'Class',0)
        old=Catalog(owner);fresh=Catalog(owner);root=Catalog(parent,owner);full=Catalog(parent,tree,owner)
        old.with_observations=lambda *a:self.fail('old metadata must never be merged')
        fresh.with_observations=lambda observed:Catalog(parent,owner) if observed is root else self.fail('unexpected merge')
        queries=[];checks=[]
        def capture(pid,identities):
            queries.append(identities)
            if identities==((owner.index,owner.serial,owner.address),):return fresh
            if identities==((parent.index,parent.serial,parent.address),):return root
            self.fail('unexpected discovery or identity')
        def reference(catalog,target,cls,*a,**kwargs):
            self.assertIs(catalog.resolve(target),parent);self.assertIs(cls,owner);return tree,full
        catalog,current,selected=stable.refresh_discovery_owned_tree(1,old,parent,tree,owner.index,
            validate_context=lambda:checks.append(True),capture=capture,read_reference=reference)
        self.assertIs(current,tree);self.assertIs(selected,full);self.assertIsNot(catalog,old)
        self.assertEqual(len(checks),3);self.assertEqual(len(queries),2)

    def test_owned_metadata_refresh_fails_closed_on_changed_context_or_identity(self):
        parent=obj(1,10,'CommonActivatableWidget',0);tree=obj(2,1001);owner=obj(3,11,'Class',0)
        old=Catalog(owner);checks=[]
        def changed():
            checks.append(True)
            if len(checks)==2:raise RuntimeError('world changed')
        with self.assertRaisesRegex(RuntimeError,'world changed'):
            stable.refresh_discovery_owned_tree(1,old,parent,tree,owner.index,validate_context=changed,
                capture=lambda *args:Catalog(owner))
        self.assertEqual(len(checks),2)
        def stale(*args):raise RuntimeError('metadata identity changed')
        with self.assertRaisesRegex(RuntimeError,'metadata identity changed'):
            stable.refresh_discovery_owned_tree(1,old,parent,tree,owner.index,validate_context=lambda:None,capture=stale)

    def test_refresh_entry_catalog_captures_stable_child_and_keeps_other_authority(self):
        parent=obj(1,10,'WBP_BaseButton_C',0);oldtree=obj(2,0);tree=obj(2,1001);owner=obj(3,11,'Class',0);title=obj(4,22,'WBP_MM_TitleScreen_C',0)
        old=Catalog(parent,oldtree,owner,title);fresh=Catalog(parent,tree,owner,title);queries=[]
        old.with_observations=lambda *a:self.fail('old catalog must never merge transitioned identity')
        def capture(pid,ids):
            queries.append(ids);self.assertIn((2,1001,tree.address),ids);self.assertNotIn((2,0,tree.address),ids)
            self.assertIn((title.index,title.serial,title.address),ids);return fresh
        current,selected=stable.refresh_owned_tree_catalog(old,parent,oldtree,tree,owner.index,capture=capture,read_reference=lambda c,*a,**k:(c.by_index[2],c))
        self.assertIs(selected,fresh);self.assertIs(current,tree);self.assertEqual(len(queries),1)

    def test_title_and_pause_reference_use_owned_tree_boundary_before_planning(self):
        from unittest.mock import Mock,patch
        from expedition33.pause_menu import PauseMenuEntry
        from expedition33.title_menu import TitleMenuEntry
        for entry_type in (PauseMenuEntry,TitleMenuEntry):
            with self.subTest(entry=entry_type.__name__):
                session,scope,parent,tree,owner,old,fresh=self.setup_case()
                entry=entry_type.__new__(entry_type);entry.scope=scope
                entry.planner=NS(_catalog=old,adopt_observations=Mock(),refresh_from=Mock())
                entry.cls=lambda name:owner
                with patch('expedition33.pause_menu.read_object_reference',return_value=(tree,old)),patch.object(stable,'stabilize_owned_tree',return_value=(fresh.by_index[2],fresh)) as acquire,patch.object(stable,'refresh_owned_tree_catalog',return_value=(fresh.by_index[2],fresh)) as refresh:
                    result=entry.reference(parent,'UserWidget','WidgetTree')
                self.assertIs(result,fresh.by_index[2]);acquire.assert_called_once_with(scope,old,parent,tree,owner)
                refresh.assert_called_once_with(old,parent,tree,fresh.by_index[2],owner.index)
                entry.planner.refresh_from.assert_called_once_with(fresh);entry.planner.adopt_observations.assert_not_called()

    def test_borrowed_title_pause_tree_never_acquires_or_refreshes(self):
        from unittest.mock import Mock,patch
        from expedition33.pause_menu import PauseMenuEntry
        session,scope,parent,tree,owner,old,fresh=self.setup_case();scope._leases=[]
        entry=PauseMenuEntry.__new__(PauseMenuEntry);entry.scope=scope;entry.cls=lambda name:owner
        entry.planner=NS(_catalog=old,adopt_observations=Mock(),refresh_from=Mock())
        with patch('expedition33.pause_menu.read_object_reference',return_value=(tree,old)),patch.object(stable,'stabilize_owned_tree') as acquire:
            self.assertIs(entry.reference(parent,'UserWidget','WidgetTree'),tree)
        acquire.assert_not_called();entry.planner.refresh_from.assert_not_called();entry.planner.adopt_observations.assert_called_once_with(old)

    def test_owned_namedslot_exact_property_and_tree_outer_chain(self):
        session,scope,parent,tree,owner,old,fresh=self.setup_case()
        parent.class_name='WBP_BaseButton_C';tree.class_name='NamedSlot';tree.outer_index=4
        container=obj(4,2001,'WidgetTree',parent.index);fresh.by_index[2].class_name='NamedSlot';fresh.by_index[2].outer_index=4
        old=Catalog(parent,tree,container,owner);fresh=Catalog(parent,fresh.by_index[2],container,owner)
        fields=[]
        def reference(catalog,target,cls,field,**kwargs):
            fields.append(field);return catalog.by_index[2],catalog
        result,selected=stable.stabilize_owned_tree(scope,old,parent,tree,owner,field='ButtonContent',read_reference=reference,capture=lambda *a:fresh)
        self.assertIs(result,fresh.by_index[2]);self.assertEqual(fields,['ButtonContent','ButtonContent'])
        # A named slot belonging to another tree/root may not be acquired.
        container.outer_index=999;session._transport.command=lambda *a:self.fail('foreign child acquired')
        with self.assertRaises(Exception):stable.stabilize_owned_tree(scope,old,parent,tree,owner,field='ButtonContent',read_reference=reference)

    def test_namedslot_changed_after_property_keeps_lease_and_no_replay(self):
        session,scope,parent,tree,owner,old,fresh=self.setup_case()
        parent.class_name='WBP_BaseButton_C';tree.class_name='NamedSlot';tree.outer_index=4
        container=obj(4,2001,'WidgetTree',parent.index);stable_child=obj(2,1001,'NamedSlot',4)
        old=Catalog(parent,tree,container,owner);fresh=Catalog(parent,stable_child,container,owner)
        calls=[];session._transport.command=lambda command,sent:(calls.append(command) or {'lease_packet':ack(sent)})
        def reference(catalog,*a,**k):return (tree,old) if catalog is old else (None,fresh)
        with self.assertRaises(Exception):stable.stabilize_owned_tree(scope,old,parent,tree,owner,field='ButtonContent',read_reference=reference,capture=lambda *a:fresh)
        self.assertEqual(calls,['stable-lease-acquire']);self.assertTrue(scope._leases[-1].active)

    def test_legacy_reference_short_circuits_before_scope_leases_and_result_serial(self):
        from unittest.mock import Mock,patch
        from expedition33.pause_menu import PauseMenuEntry
        entry=PauseMenuEntry.__new__(PauseMenuEntry);entry.scope=NS(_session=NS(_transport=NS()))
        entry.cls=lambda name:None;entry.planner=NS(_catalog=None,adopt_observations=Mock())
        with patch('expedition33.pause_menu.read_object_reference',return_value=('legacy-reference',None)):
            self.assertEqual(entry.reference(None,'UserWidget','WidgetTree'),'legacy-reference')
        entry.planner.adopt_observations.assert_called_once_with(None)

    def test_generic_borrowed_acquisition_adopts_before_read_and_uses_returned_identity(self):
        session=Session();scope=Scope(session);overlay=obj(8,0,'Overlay',9);stable_overlay=obj(8,1041,'Overlay',9)
        session._transport.command=lambda command,sent:{'lease_packet':ack(sent,serial=1041)}
        def capture(pid,ids):
            self.assertEqual(len(scope._leases),1);self.assertIsNone(scope._leases[0]._object)
            self.assertEqual(ids,((overlay.index,1041,overlay.address),));return Catalog(stable_overlay)
        lease,fresh=stable.acquire_stable(scope,overlay,capture=capture)
        self.assertIs(lease.object,stable_overlay);self.assertIn(lease,session._leases)

    def test_failed_observation_retains_acknowledged_identity_without_exposing_object(self):
        session=Session();scope=Scope(session);overlay=obj(8,0,'Overlay',9)
        calls=[]
        session._transport.command=lambda command,sent:(calls.append(command) or {'lease_packet':ack(sent,serial=1041)})
        def fail(*args):raise RuntimeError('read failed after acquisition')
        with self.assertRaisesRegex(RuntimeError,'read failed'):
            stable.acquire_stable(scope,overlay,capture=fail)
        self.assertEqual(calls,['stable-lease-acquire']);self.assertEqual(len(scope._leases),1)
        lease=scope._leases[0]
        self.assertTrue(lease.active);self.assertIsNone(lease.object)
        self.assertEqual(lease._pending_identity,(1,8,1041,overlay.address))
        self.assertIn(lease,session._leases);self.assertFalse(session.aborted)

    def test_mismatched_observation_never_publishes_the_wrong_object(self):
        session=Session();scope=Scope(session);overlay=obj(8,0,'Overlay',9)
        session._transport.command=lambda command,sent:{'lease_packet':ack(sent,serial=1041)}
        wrong=obj(8,1042,'Overlay',9)
        with self.assertRaisesRegex(Exception,'identity changed'):
            stable.acquire_stable(scope,overlay,capture=lambda *a:Catalog(wrong))
        lease=scope._leases[0]
        self.assertTrue(lease.active);self.assertIsNone(lease.object)
        self.assertEqual(lease._pending_identity,(1,8,1041,overlay.address))

    def test_owned_tree_recheck_does_not_overwrite_original_leased_identity(self):
        from unittest.mock import patch
        session,scope,parent,tree,owner,old,_=self.setup_case()
        held=obj(2,1001);wrong=obj(2,1002)
        lease=ObjectLease(session,19,held);session._leases.add(lease);scope._leases.append(lease)
        changed=Catalog(parent,wrong,owner)
        with patch.object(stable,'acquire_stable',return_value=(lease,changed)):
            with self.assertRaisesRegex(Exception,'tree identity changed'):
                stable.stabilize_owned_tree(scope,old,parent,tree,owner,
                    read_reference=lambda *a,**k:(tree,old))
        self.assertIs(lease.object,held);self.assertTrue(lease.active)

    def test_borrowed_boundary_only_acquires_zero_targets_and_discards_old_catalog(self):
        from unittest.mock import Mock,patch
        from expedition33.pause_menu import PauseMenuEntry
        session=Session();scope=Scope(session);overlay=obj(8,0,'Overlay',9);positive=obj(7,1111,'VerticalBox',9)
        new_overlay=obj(8,1041,'Overlay',9);old=Catalog(positive,overlay);fresh=Catalog(positive,new_overlay)
        lease=ObjectLease(session,32,new_overlay)
        entry=PauseMenuEntry.__new__(PauseMenuEntry);entry.scope=scope
        entry.planner=NS(_catalog=old,refresh_from=Mock())
        with patch.object(stable,'acquire_stable',return_value=(lease,fresh)) as acquire,patch.object(stable,'fresh_catalog_replacing',return_value=fresh) as refresh:
            result=entry.stabilize_borrowed_targets((positive,overlay,overlay))
        self.assertEqual(result,{8:lease});acquire.assert_called_once_with(scope,overlay)
        refresh.assert_called_once_with(old,(new_overlay,));entry.planner.refresh_from.assert_called_once_with(fresh)

    def test_title_borrowed_boundary_updates_bindings_before_fresh_authority_gate(self):
        from expedition33.title_menu import TitleMenuEntry
        title=obj(1,0,'WBP_MM_TitleScreen_C',0);box=obj(2,0,'VerticalBox',4);tree=obj(3,12,'WidgetTree',1);panel=obj(4,0,'Overlay',3)
        new_title=obj(1,1001,'WBP_MM_TitleScreen_C',0);new_box=obj(2,1002,'VerticalBox',4);new_panel=obj(4,1004,'Overlay',3)
        entry=TitleMenuEntry.__new__(TitleMenuEntry);entry.pause=title;entry.grid=box;entry.restore_tree=tree;entry.restore_panel=panel
        entry.planner=NS(_catalog=Catalog(new_title,new_box,tree,new_panel))
        binding=({'controller':(1,9,10,10000)},(5,6,7),(8,9,10),(1,0,title.address),(2,0,box.address))
        entry._title_binding=binding;owned=NS(object=new_panel)
        entry.stabilize_borrowed_targets=lambda objects:{4:owned}
        seen=[]
        def authority():
            seen.append(entry.restore_panel);self.assertIs(entry.pause,new_title);self.assertIs(entry.grid,new_box)
            self.assertEqual(entry._title_binding[3],(1,1001,new_title.address));return True
        entry._current_title=authority
        self.assertEqual(entry._prepare_borrowed_title_targets(),{4:owned});self.assertEqual(seen,[new_panel])
        entry._current_title=lambda:False
        with self.assertRaisesRegex(RuntimeError,'authority changed'):entry._prepare_borrowed_title_targets()

    def test_cross_process_generic_acquisition_rejects_before_command_or_abort(self):
        session=Session();scope=Scope(session);foreign=obj(8,0,'Overlay',9);foreign.pid=2
        session._transport.command=lambda *a:self.fail('cross-process command')
        with self.assertRaises(ValueError):stable.acquire_stable(scope,foreign)
        self.assertFalse(session.aborted);self.assertEqual(scope._leases,[])
