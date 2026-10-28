import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import patch,Mock
from test_enemy_spawn_owner import Transport
from expedition33._scope import SessionScope
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from expedition33._enemy_spawn_wire import build_request,validate_request
from expedition33.cinematics.blueprint_actor import BlueprintActor,transform


class TimelineTransport(Transport):
    timeline_blueprint_protocol=1
    enemy_grounded_spawn_protocol=2
    def command(self,name,request):
        result=super().command(name,request)
        if struct.unpack_from('<I',request,4)[0]==120:
            data=bytearray.fromhex(result['mesh_packet']);struct.pack_into('<iiQ',data,4096,10,1001,0x20000)
            return dict(mesh_packet=data.hex())
        return result


class TimelineBlueprintTests(unittest.TestCase):
    def test_python_and_native_allowlists_select_the_same_exact_classes(self):
        import re
        from pathlib import Path
        from expedition33.cinematics.blueprint_actor import PROFILES
        header=(Path(__file__).resolve().parents[1]/'native/timeline_blueprint_profiles.h').read_text()
        native=set(re.findall(r'\{"(BP_Cine_[A-Za-z0-9_]+_C)","(/Game/Characters/Heros/Cinematics/BP_Cine_[A-Za-z0-9_]+)"\}',header))
        python={(path.rsplit('.',1)[1],path.rsplit('.',1)[0]) for path in PROFILES.values()}
        self.assertEqual(native,python)
        self.assertIn('maelle',PROFILES);self.assertIn('monoco',PROFILES)

    def test_extended_blueprints_require_capability_before_construction(self):
        from expedition33.cinematics.blueprint_actor import available_profiles
        self.assertEqual(available_profiles(N()),('lune','sciel','verso'))
        self.assertEqual(available_profiles(N(timeline_extended_characters_protocol=True)),('lune','sciel','verso'))
        self.assertIn('monoco',available_profiles(N(timeline_extended_characters_protocol=1)))
        transport=TimelineTransport();scope=self.scope(transport);actor=BlueprintActor(scope)
        with self.assertRaisesRegex(RuntimeError,'newer native character runtime'):
            actor.prepare('maelle',(0,0,0,1,10,20,30,0,1,1,1,0))
        self.assertEqual(actor.state,'new');self.assertEqual(transport.calls,[])
        actor.close();scope.close()

    def test_actor_world_retirement_releases_owned_actor_without_normal_scope_close(self):
        transport=TimelineTransport();parent=self.scope(transport);actor=BlueprintActor(parent)
        ids=tuple(N(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(13))
        actor.owner.spawn_timeline_prepared(ids,(0,0,0,1,0,0,0,0,1,1,1,0));actor.state='prepared'
        consuming=N(state='armed');actor.owner._timeline_binding_owners.append(consuming)
        with patch.object(actor.scope,'close') as ordinary_close:
            self.assertFalse(actor.retire_world());self.assertFalse(actor.scope._closed)
            consuming.state='closed'
            self.assertTrue(actor.retire_world());ordinary_close.assert_not_called()
        self.assertTrue(actor.scope._closed);self.assertEqual(actor.state,'closed')
        self.assertEqual(transport.calls,[120,111]);parent.close()
    def scope(self,transport):
        transport._executable='unused-test-probe'
        return SessionScope(N(pid=123,_transport=transport,_check=lambda:None,console=N(dispatcher=N(namespace={})),_abort_ownership=Mock()))
    def test_transform_rejects_nonfinite_bool_scale_and_unnormalized_rotation(self):
        good=(0,0,0,1,10,20,30,0,1,1,1,0)
        self.assertEqual(transform(good),good)
        for index,value in ((0,float('nan')),(0,True),(3,2),(7,1),(8,2),(11,1)):
            bad=list(good);bad[index]=value
            with self.assertRaises(ValueError):transform(bad)
    def test_timeline_owner_uses_existing_construction_and_reveal_is_once_only(self):
        transport=TimelineTransport();scope=self.scope(transport);owner=EnemySpawnOwner(scope)
        ids=tuple(N(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(13))
        owner.spawn_timeline_prepared(ids,(0,0,0,1,100,200,300,0,1,1,1,0))
        self.assertEqual(owner.actor_identity,(10,1001,0x20000))
        for operation in (112,113,114,118,131,132):
            with self.assertRaisesRegex(RuntimeError,'Timeline actor permits'):owner._command(operation)
        owner.reveal_timeline();self.assertEqual(owner.phase,'visible')
        with self.assertRaises(RuntimeError):owner.reveal_timeline()
        scope.close();self.assertEqual(transport.calls,[120,221,111])
    def test_unknown_reveal_is_not_replayed_and_cleanup_remains_owned(self):
        transport=TimelineTransport();scope=self.scope(transport);owner=EnemySpawnOwner(scope)
        ids=tuple(N(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(13))
        owner.spawn_timeline_prepared(ids,(0,0,0,1,0,0,0,0,1,1,1,0));transport.fail=221
        with self.assertRaises(OSError):owner.reveal_timeline()
        self.assertEqual(owner.phase,'unknown')
        with self.assertRaises(RuntimeError):owner.reveal_timeline()
        scope.close();self.assertEqual(transport.calls,[120,221,111])
    def test_missing_or_boolean_capability_refuses_before_scope_creation(self):
        for cap in (0,True,2):
            transport=TimelineTransport();transport.timeline_blueprint_protocol=cap;scope=self.scope(transport)
            with patch('expedition33.cinematics.blueprint_actor.SessionScope') as child:
                with self.assertRaises(RuntimeError):BlueprintActor(scope)
                child.assert_not_called()
            scope.close()
    def test_reveal_request_carries_no_new_identities_or_pose(self):
        request=build_request(123,221);validate_request(request)
        for at in (24,88,2000,4096):
            bad=bytearray(request);bad[at]=1
            with self.assertRaises(ValueError):validate_request(bytes(bad))
    def test_adapter_refuses_wrong_map_before_class_loading(self):
        transport=TimelineTransport();scope=self.scope(transport);actor=BlueprintActor(scope)
        from contextlib import nullcontext
        with patch('expedition33.cinematics.blueprint_actor.shared_operation',return_value=nullcontext()),\
             patch('expedition33.cinematics.controller_anchor.for_scope',return_value=N(context=lambda:{'world_path':'/Game/Other.Other'})),\
             patch('expedition33.cinematics.blueprint_actor.load_class') as loader:
            with self.assertRaisesRegex(ValueError,'QA map'):actor.prepare('lune',(0,0,0,1,0,0,0,0,1,1,1,0))
            loader.assert_not_called()
        self.assertTrue(actor.close());self.assertEqual(transport.calls,[]);scope.close()
    def test_deferred_actor_cleanup_preserves_scope_and_owner(self):
        transport=TimelineTransport();scope=self.scope(transport);actor=BlueprintActor(scope)
        actor.state='prepared'
        with patch.object(actor.owner,'close',return_value=False),patch.object(actor.scope,'close') as close:
            self.assertFalse(actor.close());self.assertEqual(actor.state,'prepared');close.assert_not_called()
        self.assertTrue(actor.close());scope.close()

    def test_current_world_requires_exact_native_capability_before_loading_class(self):
        from contextlib import nullcontext
        for cap in (0,True,'1',1):
            transport=TimelineTransport();transport.timeline_current_world_protocol=cap
            scope=self.scope(transport);actor=BlueprintActor(scope)
            with patch('expedition33.cinematics.blueprint_actor.shared_operation',return_value=nullcontext()),\
                 patch('expedition33.cinematics.controller_anchor.for_scope',return_value=N(context=lambda:{'world_path':'/Game/Other.Other'})),\
                 patch('expedition33.cinematics.blueprint_actor.load_class',side_effect=RuntimeError('class loading reached')) as loader:
                with self.assertRaisesRegex((ValueError,RuntimeError),'class loading reached' if type(cap) is int and cap==1 else 'QA map'):
                    actor.prepare('lune',(0,0,0,1,0,0,0,0,1,1,1,0))
                self.assertEqual(loader.call_count,int(type(cap) is int and cap==1))
            self.assertTrue(actor.close());scope.close()
