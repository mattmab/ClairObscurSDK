import struct
import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import _story_world_configure_wire as wire, _invocation_wire as callwire
from expedition33.invocation import CallPlan,Parameter
from expedition33.story_world_configure import execute,available
from expedition33.story_world import WorldElement
from expedition33._ui_batch import pack_sparse

def obj(i):return N(index=i,serial=1000+i,address=i*0x10000,name='ObservedFunction')
def identity(i):return (i,1000+i,i*0x10000)
WALL='/Game/LevelTools/InvisibleWalls/BP_InvisibleWall_NavModifier.BP_InvisibleWall_NavModifier_C:SetInvisibleWallEnabled'
def plans(wall=True,mesh=True):
    rows=[(13,'/Script/Engine.SceneComponent:SetMobility','NewMobility',2),(12,'/Script/Engine.Actor:SetActorScale3D','NewScale3D',(1.,2.,3.))]
    if wall and mesh:rows.append((14,'/Script/Engine.SceneComponent:SetRelativeScale3D','NewScale3D',(2.,3.,4.)))
    rows.append((12,WALL if wall else '/Script/Engine.Actor:SetActorTickEnabled','Enabled' if wall else 'bEnabled',False))
    rows.extend(((12,'/Script/Engine.Actor:SetActorEnableCollision','bNewActorEnableCollision',wall),
        (12,'/Script/Engine.Actor:SetActorHiddenInGame','bNewHidden',wall),(13,'/Script/Engine.SceneComponent:SetMobility','NewMobility',0)))
    result=[]
    for number,(actor,path,name,value) in enumerate(rows):
        if type(value) is tuple:
            field=Parameter(name,'StructProperty',0,24,1,0x80,constraint=obj(30),pod_profile='/Script/CoreUObject.Vector');data=struct.pack('<3d',*value);version=2
        elif type(value) is bool:
            field=Parameter(name,'BoolProperty',0,1,1,0x80,boolean_encoding=0xff010001);data=bytes((int(value),));version=8 if path==WALL else 1
        else:field=Parameter(name,'ByteProperty',0,1,1,0x80);data=bytes((value,));version=1
        result.append((path,CallPlan(obj(actor),obj(20+number),0,0x13937a0 if version==8 else 0,len(data),max(8,len(data)),65535,(field,),data,(),version)))
    return result
def encoded(wall=True,mesh=True):return tuple(wire.encode_plan(p) for _,p in plans(wall,mesh))
def request(wall=True,mesh=True):
    return wire.encode(99,'wall' if wall else 'portal',identity(10),identity(11),identity(12),identity(13),identity(14) if wall else None,0,encoded(wall,mesh))
def response(sent,requests,*,error=0,failed=None,unknown=False):
    out=bytearray(wire.SIZE);out[:wire.HEADER]=sent[:wire.HEADER];at=wire.HEADER
    for i,request in enumerate(requests):
        packet=bytearray(request);struct.pack_into('<II',packet,32,(2 if unknown else 0) if i==failed else 1,201 if i==failed else 0)
        packed=pack_sparse(packet);struct.pack_into('<I',out,at,len(packed));at+=4;out[at:at+len(packed)]=packed;at+=len(packed)
    struct.pack_into('<II',out,8,error,len(requests));struct.pack_into('<I',out,32,at);return bytes(out).hex()

class WorldConfigurationWireTests(unittest.TestCase):
    def test_original_native_and_blueprint_calls_share_correlated_scalar_receipts(self):
        for wall,mesh in ((False,False),(True,False),(True,True)):
            calls=encoded(wall,mesh);sent=request(wall,mesh)
            receipts=wire.decode(sent,calls,response(sent,calls))
            self.assertEqual(len(receipts),len(calls));self.assertTrue(all(r.outcome=='dispatch_returned' for r in receipts))
    def test_partial_unknown_and_rejected_outcomes_have_exact_prefixes(self):
        calls=encoded();sent=request()
        for unknown,error in ((False,4351),(True,4352)):
            with self.assertRaises(wire.WorldConfigurationError) as caught:
                wire.decode(sent,calls,response(sent,calls[:3],error=error,failed=2,unknown=unknown))
            self.assertEqual(len(caught.exception.receipts),3);self.assertEqual(caught.exception.unknown,unknown)
        with self.assertRaises(wire.WorldConfigurationError) as caught:wire.decode(sent,calls,response(sent,(),error=4350))
        self.assertEqual(caught.exception.outcome,'not_dispatched')
    def test_changed_owner_world_component_mobility_or_bounds_rejected(self):
        sent=request();calls=encoded();good=bytes.fromhex(response(sent,calls))
        for at in (16,24,28,32,40,56,72,88,104,120,10000):
            bad=bytearray(good);bad[at]^=1
            with self.assertRaises(ValueError):wire.decode(sent,calls,bad.hex())
        with self.assertRaises(ValueError):wire.decode(sent,calls,response(sent,calls[:2]))
        with self.assertRaises(ValueError):wire.decode(sent,calls,response(sent,calls[:2],error=4350))
    def test_admission_rejects_non_scalar_ownership_and_packet_padding(self):
        for at in (8,12,24,36,124,wire.SIZE-1):
            bad=bytearray(request());bad[at]^=1
            with self.assertRaises(ValueError):wire.validate_request(bytes(bad))
        calls=list(encoded());bad=bytearray(calls[0]);struct.pack_into('<I',bad,callwire.SIZE+4,1);calls[0]=bytes(bad)
        with self.assertRaises(ValueError):wire.encode(99,'wall',identity(10),identity(11),identity(12),identity(13),identity(14),0,calls)

class WorldConfigurationLifecycleTests(unittest.TestCase):
    def setup_element(self,wall=True,mesh=True):
        transport=N(story_world_configure_protocol=1,timeline_actor_pool_protocol=1,command=Mock())
        session=N(_transport=transport);scope=N(pid=7,_session=session,_check=Mock(),_lease_context=nullcontext,_world_binding_token=((7,*identity(10)),(),(),()))
        construction=bytearray(wire.SIZE);struct.pack_into('<II',construction,0,3,120);struct.pack_into('<Q',construction,16,99)
        for at,i in ((88,11),(120,10),(4096,12)):struct.pack_into('<iiQ',construction,at,*identity(i))
        owner=N(last_operation=120,last_response=bytes(construction),phase='spawned',_owner=99)
        actor=N(owner=owner,scope=scope,state='prepared',identity=identity(12))
        element=N(actor=actor,state='preparing');rows=plans(wall,mesh);paths={p.function.index:path for path,p in rows}
        planner=N(_scope=lambda:scope,_catalog=N(path_name=lambda fn:paths[fn.index]))
        calls=[N(_check=Mock(return_value=(planner,session)),_plan=p) for _,p in rows]
        transport.command.side_effect=lambda _,sent:{'mesh_packet':response(sent,encoded(wall,mesh))}
        return element,calls,planner,transport
    def test_six_or_seven_calls_use_one_handoff_without_replaying(self):
        for wall,mesh in ((False,False),(True,False),(True,True)):
            element,calls,_,transport=self.setup_element(wall,mesh)
            args=(element,'wall' if wall else 'portal',obj(13),obj(14) if wall else None,0,calls)
            self.assertTrue(execute(*args));self.assertEqual(len(element._configuration_receipts),len(calls))
            transport.command.assert_called_once()
            with self.assertRaisesRegex(RuntimeError,'never replayed'):execute(*args)
            transport.command.assert_called_once()
    def test_stale_admission_or_plan_is_rejected_before_any_dispatch(self):
        for mode in ('scope','world','receipt','revoked','function'):
            element,calls,planner,transport=self.setup_element()
            if mode=='scope':planner._scope=lambda:object()
            elif mode=='world':element.actor.scope._world_binding_token=((7,*identity(15)),(),(),())
            elif mode=='receipt':element.actor.owner.phase='visible'
            elif mode=='revoked':calls[-1]._check.side_effect=RuntimeError('revoked plan')
            else:planner._catalog.path_name=lambda fn:'Unexpected'
            with self.assertRaises((ValueError,RuntimeError)):execute(element,'wall',obj(13),obj(14),0,calls)
            transport.command.assert_not_called()
    def test_partial_or_missing_ack_preserves_owner_and_prohibits_replay(self):
        for mode in ('prefix','lost','rejected'):
            element,calls,_,transport=self.setup_element();owner=element.actor.owner
            if mode=='lost':transport.command.side_effect=RuntimeError('lost ACK')
            elif mode=='prefix':transport.command.side_effect=lambda _,sent:{'mesh_packet':response(sent,encoded()[:2],error=4352,failed=1,unknown=True)}
            else:transport.command.side_effect=lambda _,sent:{'mesh_packet':response(sent,(),error=4350)}
            with self.assertRaises(wire.WorldConfigurationError):execute(element,'wall',obj(13),obj(14),0,calls)
            self.assertIs(element.actor.owner,owner);self.assertEqual(owner.phase,'spawned')
            self.assertEqual(element.state,'failed' if mode=='rejected' else 'unknown')
            with self.assertRaisesRegex(RuntimeError,'never replayed'):execute(element,'wall',obj(13),obj(14),0,calls)
            transport.command.assert_called_once()
    def test_capability_requires_exact_integer_protocol(self):
        element,_,_,transport=self.setup_element();self.assertTrue(available(element.actor.scope))
        for value in (True,2,'1',None):
            transport.story_world_configure_protocol=value;self.assertFalse(available(element.actor.scope))

class WorldElementCompatibilityTests(unittest.TestCase):
    def test_public_preparation_keeps_original_order_and_uses_batch_only_when_supported(self):
        for wall in (False,True):
            for batched in (False,True):
                events=[];root=obj(13);mesh=obj(14);target=obj(12)
                catalog=N(pid=7,by_index={12:target},objects=(),with_observations=lambda c:catalog,find_path=lambda path:path)
                def prepare(obj,path,**arguments):return N(invoke=lambda:nullcontext(events.append(path)),path=path)
                planner=N(prepare=prepare,prepare_blueprint=prepare)
                resources=N(catalog=lambda scope,names:catalog,movement_planner=lambda scope,c:nullcontext(planner))
                scope=N(pid=7,_session=N(_story_construction_resources=resources))
                actor=N(scope=scope,identity=identity(12),state='prepared',prepare_collision_wall=Mock(),prepare_portal_visual=Mock())
                values=[(N(values={('x','RootComponent'):root,('x','SM_InvisibleWalls'):mesh},errors=()),catalog),(N(values={('x','Mobility'):0},errors=()),catalog)]
                with patch('expedition33.story_world.BlueprintActor',return_value=actor),patch('expedition33.story_world.capture_selected_values',return_value=(catalog,{12:values[0][0]})) as root_read,patch('expedition33.story_world.read_values_with_references',return_value=values[1]),patch('expedition33.story_world.story_world_configure.available',return_value=batched),patch('expedition33.story_world.story_world_configure.execute') as batch:
                    element=WorldElement(None);element.prepare('wall' if wall else 'portal',[0.,0.,0.,1.,0.,0.,0.,0.,1.,1.,1.,0.],mesh_scale=[2.,3.,4.] if wall else None)
                    expected=[path for path,_ in plans(wall,wall)]
                    if batched:
                        batch.assert_called_once();self.assertEqual([call.path for call in batch.call_args.args[-1]],expected);self.assertEqual(events,[])
                    else:self.assertEqual(events,expected);batch.assert_not_called()
                    self.assertEqual(element.state,'ready')
                    root_read.assert_called_once_with(7,(identity(12),),fields=('SM_InvisibleWalls','RootComponent') if wall else ('RootComponent',),references=True)

if __name__=='__main__':unittest.main()
