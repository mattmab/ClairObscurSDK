import unittest
from dataclasses import replace
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog,CatalogObject,ClassRelation
from expedition33.story_construction import StoryConstruction


def metadata_fixture():
    classes=[ClassRelation(i,1,name,parent,40+i*8) for i,(name,parent) in enumerate((
        ('Object',-1),('Class',0),('Package',0),('Function',0),('ScriptStruct',0),
        ('DataTable',0),('Actor',0),('BlueprintGeneratedClass',1),('AnimBlueprintGeneratedClass',7)))]
    def obj(index,name,cls,outer=-1,flags=0):
        return CatalogObject(123,index,1,0x10000+index*256,name,classes[cls].name,'Class',
            cls,outer,1 if outer>=0 else 0,flags,0)
    objects=[obj(i,c.name,1,10 if i==6 else 11) for i,c in enumerate(classes)]
    objects += [obj(10,'/Script/Engine',2),obj(11,'/Script/CoreUObject',2),obj(12,'/Game/Story',2),
        obj(13,'K2_TeleportTo',3,6),obj(14,'Story_C',8,12),obj(15,'StartConversation',3,14),
        obj(16,'Vector',4,11),obj(17,'StoryData',5,12),obj(18,'Default__Actor',6,10,0x10),
        obj(19,'RuntimeActor',6),obj(20,'StoryStruct',4,12),obj(21,'SetActorEnableCollision',3,6)]
    return Catalog(123,objects,classes)


def prepared_fixture(indices=(13,15,16,17,18,19,20,21,6)):
    catalog=metadata_fixture();owner=StoryConstruction.__new__(StoryConstruction)
    owner.session=object();scope=N(pid=123,_check=Mock(),_session=owner.session)
    owner.scope=N(pid=123,_check=Mock());owner.metadata=tuple(catalog.by_index[i] for i in indices)
    owner._metadata_leases=tuple(N(object=o,active=True) for o in owner.metadata)
    paths=tuple(catalog.path_name(o) for o in owner.metadata)
    with patch('expedition33.story_construction.PATHS',paths), \
            patch('expedition33.story_construction.capture_selected',return_value=catalog) as read:
        owner._retain_catalog()
    return owner,scope,catalog,read

class ConstructionTests(unittest.TestCase):
    def test_movement_plan_adopts_fresh_observations_and_refuses_other_session(self):
        owner=StoryConstruction.__new__(StoryConstruction);owner.session=object()
        owner.scope=N(_check=Mock());owner.movement_observations=object()
        scope=N(_check=Mock(),_session=owner.session,invocation_planner=Mock())
        fresh=object();planner=owner.movement_planner(scope,fresh)
        planner.adopt_observations.assert_called_once_with(fresh)
        scope.invocation_planner.assert_called_once_with(observations=owner.movement_observations,selected_results=True)
        scope._session=object()
        with self.assertRaisesRegex(RuntimeError,'another session'):owner.movement_planner(scope,fresh)
        scope.invocation_planner.assert_called_once()

    def test_failed_current_observation_adoption_closes_unused_plan(self):
        owner=StoryConstruction.__new__(StoryConstruction);owner.session=object()
        owner.scope=N(_check=Mock());owner.movement_observations=object()
        planner=Mock();planner.adopt_observations.side_effect=RuntimeError('identity changed')
        scope=N(_check=Mock(),_session=owner.session,invocation_planner=Mock(return_value=planner))
        with self.assertRaisesRegex(RuntimeError,'identity changed'):owner.movement_planner(scope,object())
        planner.close.assert_called_once();planner.prepare.assert_not_called()

    def test_only_held_function_and_native_struct_roots_are_retained_once(self):
        owner,scope,catalog,read=prepared_fixture()
        self.assertEqual(set(owner._retained_roots),{13,15,16,21})
        read.assert_called_once_with(123,tuple((i,1,catalog.by_index[i].address) for i in (13,15,16,21)))
        self.assertTrue({17,18,19,20}.isdisjoint(owner._retained_catalog.by_index))
        with patch('expedition33.story_construction.capture_selected') as fresh, \
                patch('expedition33.story_construction.capture_matching') as scan:
            for _ in range(2):
                selected=owner.catalog(scope,('K2_TeleportTo','Vector'))
                self.assertEqual(selected.find_path('/Script/Engine.Actor:K2_TeleportTo').index,13)
                self.assertEqual(selected.find_path('/Script/CoreUObject.Vector').index,16)
                self.assertTrue({15,17,18,19,20,21}.isdisjoint(selected.by_index))
        fresh.assert_not_called();scan.assert_not_called()

    def test_tables_cdos_runtime_and_unadmitted_types_are_always_fresh(self):
        owner,scope,catalog,_=prepared_fixture()
        indices=(17,18,19,20,6);names=tuple(catalog.by_index[i].name for i in indices)
        first=catalog.subset(tuple(catalog.by_index[i] for i in indices))
        second=Catalog(123,[replace(o,object_flags=0x80) if o.index==19 else o for o in first.objects],tuple(first.classes.values()))
        with patch('expedition33.story_construction.capture_selected',side_effect=(first,second)) as read:
            self.assertIs(owner.catalog(scope,names),first)
            self.assertIs(owner.catalog(scope,names),second)
        self.assertEqual(read.call_count,2)
        read.assert_called_with(123,tuple((i,1,catalog.by_index[i].address) for i in indices))

    def test_mixed_catalog_preserves_fresh_root_and_excludes_unrequested_metadata(self):
        owner,scope,catalog,_=prepared_fixture();fresh=catalog.subset((catalog.by_index[18],))
        with patch('expedition33.story_construction.capture_selected',return_value=fresh) as read:
            result=owner.catalog(scope,('Default__Actor','K2_TeleportTo'))
        read.assert_called_once_with(123,((18,1,catalog.by_index[18].address),))
        self.assertIs(result.by_index[18],fresh.by_index[18]);self.assertIn(13,result.by_index)
        self.assertNotIn(21,result.by_index)
        self.assertNotIn(18,owner._retained_catalog.by_index)

    def test_mixed_fresh_owner_recycling_is_rejected_without_fallback(self):
        owner,scope,catalog,_=prepared_fixture();fresh=catalog.subset((catalog.by_index[18],))
        objects=[replace(o,serial=9) if o.index==6 else o for o in fresh.objects]
        classes=[replace(c,serial=9) if c.index==6 else c for c in fresh.classes.values()]
        changed=Catalog(123,objects,classes)
        with patch('expedition33.story_construction.capture_selected',return_value=changed) as read, \
                patch('expedition33.story_construction.capture_matching') as scan:
            with self.assertRaisesRegex(RuntimeQueryError,'identity changed'):
                owner.catalog(scope,('Default__Actor','K2_TeleportTo'))
        read.assert_called_once();scan.assert_not_called()

    def test_same_identity_owner_reparenting_is_rejected(self):
        owner,scope,catalog,_=prepared_fixture();fresh=catalog.subset((catalog.by_index[18],catalog.by_index[11]))
        changed=Catalog(123,[replace(o,outer_index=11) if o.index==6 else o for o in fresh.objects],tuple(fresh.classes.values()))
        with patch('expedition33.story_construction.capture_selected',return_value=changed):
            with self.assertRaisesRegex(RuntimeError,'owner or root changed'):
                owner.catalog(scope,('Default__Actor','K2_TeleportTo'))

    def test_expired_or_changed_metadata_lease_rejects_local_reuse(self):
        owner,scope,catalog,_=prepared_fixture();lease=owner._retained_roots[13][1]
        with patch('expedition33.story_construction.capture_selected') as read:
            lease.active=False
            with self.assertRaisesRegex(RuntimeError,'lease expired'):owner.catalog(scope,('K2_TeleportTo',))
            lease.active=True;lease.object=replace(lease.object,serial=9)
            with self.assertRaisesRegex(RuntimeQueryError,'identity changed'):owner.catalog(scope,('K2_TeleportTo',))
        read.assert_not_called()

    def test_closed_and_foreign_scope_rejects_before_any_catalog_or_read(self):
        owner,scope,catalog,_=prepared_fixture()
        with patch('expedition33.story_construction.capture_selected') as read:
            with self.assertRaisesRegex(RuntimeError,'another session'):
                owner.catalog(N(_check=Mock(),_session=object()),('K2_TeleportTo',))
            owner.scope._check.side_effect=RuntimeError('resource closed')
            with self.assertRaisesRegex(RuntimeError,'resource closed'):owner.catalog(scope,('K2_TeleportTo',))
            owner.scope._check.side_effect=None;scope._check.side_effect=RuntimeError('world scope closed')
            with self.assertRaisesRegex(RuntimeError,'world scope closed'):owner.catalog(scope,('K2_TeleportTo',))
        read.assert_not_called()

    def test_exact_root_provenance_must_match_after_acquisition(self):
        catalog=metadata_fixture();owner=StoryConstruction.__new__(StoryConstruction)
        owner.scope=N(pid=123);owner._metadata_leases=(N(object=catalog.by_index[13],active=True),)
        with patch('expedition33.story_construction.PATHS',('/Script/Engine.Actor:WrongFunction',)), \
                patch('expedition33.story_construction.capture_selected',return_value=catalog):
            with self.assertRaisesRegex(RuntimeError,'owner or root changed'):owner._retain_catalog()
        self.assertFalse(hasattr(owner,'_retained_catalog'))
    def test_world_identity_is_fresh_and_must_match_the_scope_admission(self):
        owner=StoryConstruction.__new__(StoryConstruction)
        expected=(1,2,3,0x10000);owner.anchor=N(context=Mock(return_value={'world':expected}))
        scope=N(_world_binding_token=(expected,))
        self.assertEqual(owner.context(scope)['world'],expected)
        owner.anchor.context.return_value={'world':(1,4,5,0x20000)}
        with self.assertRaisesRegex(RuntimeError,'scope admission'):owner.context(scope)
        self.assertEqual(owner.anchor.context.call_count,2)

    def test_observe_batches_runtime_targets_cdo_and_properties_without_a_catalog_read(self):
        owner,scope,catalog,_=prepared_fixture()
        identities=((19,1,catalog.by_index[19].address),)
        observed=catalog.subset((catalog.by_index[18],catalog.by_index[19]));values={19:object()}
        with patch('expedition33.values.capture_selected_values',return_value=(observed,values)) as read, \
                patch('expedition33.story_construction.capture_selected',side_effect=AssertionError('No separate catalog')):
            result,copied=owner.observe(scope,('Default__Actor','K2_TeleportTo'),identities,fields=('Pawn',))
        read.assert_called_once_with(123,(*identities,(18,1,catalog.by_index[18].address)),fields=('Pawn',),references=True)
        self.assertIs(copied,values);self.assertIn(13,result.by_index);self.assertIn(19,result.by_index)
        self.assertNotIn(21,result.by_index)

    def test_observe_does_not_accept_recycled_cdo_or_stale_metadata_lease(self):
        owner,scope,catalog,_=prepared_fixture()
        observed=catalog.subset((catalog.by_index[18],catalog.by_index[19]))
        changed=Catalog(123,[replace(o,serial=9) if o.index==18 else o for o in observed.objects],tuple(observed.classes.values()))
        with patch('expedition33.values.capture_selected_values',return_value=(changed,{})) as read:
            with self.assertRaisesRegex(RuntimeQueryError,'identity changed'):
                owner.observe(scope,('Default__Actor','K2_TeleportTo'),((19,1,catalog.by_index[19].address),),fields=('Pawn',))
        read.assert_called_once()
        owner._retained_roots[13][1].active=False
        with patch('expedition33.values.capture_selected_values') as read:
            with self.assertRaisesRegex(RuntimeError,'lease expired'):
                owner.observe(scope,('K2_TeleportTo',),((19,1,catalog.by_index[19].address),),fields=('Pawn',))
        read.assert_not_called()
