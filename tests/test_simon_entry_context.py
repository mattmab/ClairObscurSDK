from dataclasses import FrozenInstanceError
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import unittest

from expedition33 import _simon_entry_context as m
from expedition33.values import StoredArray,StoredStruct,StoredValues


class SimonEntryContextTests(unittest.TestCase):
    def setUp(self):
        def obj(index,name,cls,outer=-1):
            return N(pid=123,index=index,serial=1,address=0x10000+index*256,name=name,class_name=cls,
                class_index=index+20,outer_index=outer,outer_serial=1,object_flags=0,item_flags=0)
        self.zone=obj(1,m.ZONE_NAME,'BP_GameActionTriggerZone_C')
        self.scene=obj(2,'DefaultSceneRoot','SceneComponent',1)
        self.sphere=obj(3,'Sphere','SphereComponent',1)
        self.box=obj(4,'TriggerBox','BoxComponent',1)
        self.interaction=obj(5,'InteractionLocation','SceneComponent',1)
        self.controller=obj(6,'Controller','Controller')
        self.pawn=obj(7,'Pawn','BP_jRPG_Character_World_C')
        self.pawn_root=obj(8,'Capsule','CapsuleComponent',7)
        self.root=obj(9,'BossSimon','BP_GameAction_Sequential_C')
        self.vector_type=obj(10,'Vector','ScriptStruct')
        self.rotator_type=obj(11,'Rotator','ScriptStruct')
        self.wrapper_type=obj(12,'GameAction_Wrapper','ScriptStruct')
        self.world=obj(13,'World','World')
        objects={o.index:o for o in (self.zone,self.scene,self.sphere,self.box,self.interaction,self.controller,
            self.pawn,self.pawn_root,self.root,self.vector_type,self.rotator_type,self.wrapper_type,self.world)}
        classes={21:m.ZONE_CLASS,22:'/Script/Engine.SceneComponent',23:'/Script/Engine.SphereComponent'}
        objects.update({i:N(path=path) for i,path in classes.items()})
        paths={1:m.ZONE_PATH,9:m.simon_source.ROOT,10:'/Script/CoreUObject.Vector',
            11:'/Script/CoreUObject.Rotator',12:m.simon_source.WRAPPER_CLASS}
        self.catalog=N(objects=(self.zone,),by_index=objects,
            resolve=lambda obj:objects[obj.index],path_name=lambda obj:getattr(obj,'path',paths.get(getattr(obj,'index',-1),'Other')),
            with_observations=lambda other:self.catalog)
        self.context=dict(controller=m.identity(self.controller),world=m.identity(self.world),world_path=m.simon_source.WORLD)
        self.scope=N(pid=123,_session=N(_transport=N(_executable='candidate')),_check=Mock())
        self.position=(21001.87,6813.34,-402264.45)
        self.parents={2:None,3:self.scene,8:None}
        self.frames={2:(m.ROOT_LOCATION,m.ROOT_ROTATION,(1.,1.,1.)),
            3:(m.SPHERE_LOCATION,m.SPHERE_ROTATION,m.SPHERE_SCALE),8:(self.position,(0.,0.,0.),(1.,1.,1.))}
        self.wrapper=StoredStruct(self.wrapper_type,{'GameActionReference':self.root,'GameActionInline':None},{},
            {'GameActionReference':'ObjectProperty','GameActionInline':'ObjectProperty'},False)
        self.components=StoredArray((self.box,self.sphere,self.interaction),3)
        self.radius=32.;self.overlap=True
        self.enterContext(patch.object(m,'ReadBatch'))
        self.enterContext(patch.object(m,'active_reader',return_value=object()))
        self.context_read=self.enterContext(patch.object(m,'controller_context',return_value=self.context))
        self.enterContext(patch.object(m,'capture_matching',return_value=self.catalog))
        self.enterContext(patch.object(m,'capture_selected',return_value=self.catalog))
        self.membership=self.enterContext(patch.object(m,'observe_actor_membership'))
        self.read=self.enterContext(patch.object(m,'read_values_with_references',side_effect=self.values))

    def vector(self,value,rotation=False):
        names=('Pitch','Yaw','Roll') if rotation else ('X','Y','Z')
        return StoredStruct(self.rotator_type if rotation else self.vector_type,dict(zip(names,value)),{},
            {name:'DoubleProperty' for name in names},False)

    def values(self,catalog,obj,*,fields):
        data={};types={}
        if obj.index in self.frames:
            location,rotation,scale=self.frames[obj.index]
            data.update(RelativeLocation=self.vector(location),RelativeRotation=self.vector(rotation,True),
                RelativeScale3D=self.vector(scale),AttachParent=self.parents[obj.index])
            types.update(RelativeLocation='StructProperty',RelativeRotation='StructProperty',
                RelativeScale3D='StructProperty',AttachParent='ObjectProperty')
        if obj.index==1:
            data.update(GameActionOnOverlap=self.wrapper,DefaultSceneRoot=self.scene,TriggerComponents=self.components)
            types.update(GameActionOnOverlap='StructProperty',DefaultSceneRoot='ObjectProperty',TriggerComponents='ArrayProperty')
        if obj.index==3:
            data.update(SphereRadius=self.radius,bGenerateOverlapEvents=self.overlap)
            types.update(SphereRadius='FloatProperty',bGenerateOverlapEvents='BoolProperty')
        if obj.index==6:data['Pawn']=self.pawn;types['Pawn']='ObjectProperty'
        if obj.index==7:data['RootComponent']=self.pawn_root;types['RootComponent']='ObjectProperty'
        return StoredValues(obj,{(obj.index,n):data[n] for n in fields},{},
            {(obj.index,n):types[n] for n in fields}),catalog

    def require(self):
        return m.require_original_entry(self.scope,self.context,root=self.root)

    def test_current_original_source_envelope_admitted_and_immutable(self):
        result=self.require()
        self.assertEqual(result.position,self.position)
        self.assertEqual(result.policy,'conservative_authored_trigger_sphere')
        self.assertEqual(self.membership.call_count,2)
        self.assertAlmostEqual(result.radius,1407.0272216796875)
        self.assertEqual(self.context_read.call_count,2)
        with self.assertRaises(FrozenInstanceError):result.radius=99999

    def test_far_entry_and_tested_but_outside_point_conservatively_reject(self):
        for point in ((0.,0.,0.),(21601.8,4385.84,-402264.45)):
            self.frames[8]=(point,(0.,0.,0.),(1.,1.,1.))
            with self.assertRaisesRegex(m.SimonEntryNotReady,'optional source-context qualification'):self.require()

    def test_bad_copied_positions_reject(self):
        for point in ((True,1,2),(1,float('nan'),2),(1,2),(1,2,1e8)):
            with self.assertRaises(ValueError):m.require_inside(point)

    def test_changed_source_geometry_or_attachment_rejects(self):
        self.frames[2]=((m.ROOT_LOCATION[0]+1,*m.ROOT_LOCATION[1:]),m.ROOT_ROTATION,(1.,1.,1.))
        with self.assertRaisesRegex(RuntimeError,'authored source'):self.require()
        self.frames[2]=(m.ROOT_LOCATION,m.ROOT_ROTATION,(1.,1.,1.))
        self.parents[3]=None
        with self.assertRaisesRegex(RuntimeError,'authored source'):self.require()

    def test_changed_radius_overlap_and_components_reject(self):
        self.radius=64.
        with self.assertRaisesRegex(RuntimeError,'radius/overlap'):self.require()
        self.radius=32.;self.overlap=False
        with self.assertRaisesRegex(RuntimeError,'radius/overlap'):self.require()
        self.overlap=True;self.components=StoredArray((self.box,self.sphere),3)
        with self.assertRaisesRegex(RuntimeError,'trigger components'):self.require()

    def test_wrong_original_action_reference_rejects(self):
        self.wrapper=StoredStruct(self.wrapper_type,{'GameActionReference':self.box,'GameActionInline':None},{},
            dict(self.wrapper.types),False)
        with self.assertRaisesRegex(RuntimeError,'retained Simon graph'):self.require()

    def test_foreign_world_or_membership_rejects_without_admission(self):
        self.context=dict(self.context,world_path='/Game/Other.Other')
        with self.assertRaisesRegex(RuntimeError,'Exact original Simon world'):self.require()
        self.context['world_path']=m.simon_source.WORLD
        self.membership.side_effect=RuntimeError('level is not current')
        with self.assertRaisesRegex(RuntimeError,'not current'):self.require()

    def test_current_pawn_root_ownership_and_attachment_required(self):
        self.pawn_root.outer_serial=9
        with self.assertRaisesRegex(RuntimeError,'root ownership'):self.require()
        self.pawn_root.outer_serial=1;self.parents[8]=self.scene
        with self.assertRaisesRegex(RuntimeError,'Unattached exploration pawn'):self.require()

    def test_context_change_is_terminal_preflight_error(self):
        self.context_read.side_effect=[self.context,dict(self.context,controller=(123,100,2,0x20000))]
        with self.assertRaisesRegex(RuntimeError,'changed during'):self.require()

    def test_closed_scope_prevents_all_observation(self):
        self.scope._check.side_effect=RuntimeError('closed')
        with self.assertRaisesRegex(RuntimeError,'closed'):self.require()
        self.read.assert_not_called()
