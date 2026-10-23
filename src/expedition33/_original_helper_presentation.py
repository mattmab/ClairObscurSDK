"""Bounded original Sirene presentation using retained source references.

No asset-name fabrication, CDO writes, general property writes or native opcodes.
The caller's encounter scope retains the source World until owned roots retire.
"""
import math
from .assets import load_generated_world
from .catalog import capture_matching,capture_selected
from .values import read_values_with_references
from ._reader import ReadBatch
from .original_trigger_sources import _copy
from .cinematics.original_game_action import controller_context

HELPER='/Game/Characters/Enemies/Axons/Sirene/BP_DummyEnemy_Sirene.BP_DummyEnemy_Sirene_C'
SOURCE_WORLD='/Game/Levels/Siren/Level_Sirene_Main_V2/_Generated_/38DFJMPD8YROH9U24BMJRTFIY.Level_Sirene_Main_V2'
SOURCE_ACTOR=SOURCE_WORLD+':PersistentLevel.BP_DummyEnemy_Sirene_C_UAID_581122C6E7A528A401_1984609581'
NODES={'FX_Petals','FX_Petals1','FX_Ribbon01','FX_Ribbon02','FX_Ribbon03','FX_Ribbon04',
    'DefaultSceneRoot','Body','Hair_Sirene_Axon_skl','Spline_Ballet1','SM_sirene_ball_ball_1_low',
    'SM_sirene_ball_ring_1_low','SM_sirene_ball_ring_2_low','Scene_Attach_Spline_1','Scene_Attach_Spline_2','Scene_Attach_Spline_3'}

def _identity(obj):return obj.index,obj.serial,obj.address

def _normalize(value):
    if isinstance(value,dict):
        if value.get('errors') or value.get('truncated'):raise RuntimeError('Incomplete source component values')
        if 'fields' in value:return {k:_normalize(v) for k,v in value['fields'].items()}
        if 'items' in value:
            if value.get('length')!=len(value['items']):raise RuntimeError('Incomplete source component array')
            return [_normalize(v) for v in value['items']]
        return {k:_normalize(v) for k,v in value.items()}
    if isinstance(value,list):return [_normalize(v) for v in value]
    return value

def _equal(left,right):
    if type(left) in (int,float) and type(right) in (int,float):
        return math.isclose(left,right,rel_tol=1.e-7,abs_tol=1.e-4)
    if type(left)!=type(right):return False
    if isinstance(left,dict):return left.keys()==right.keys() and all(_equal(v,right[k]) for k,v in left.items())
    if isinstance(left,list):return len(left)==len(right) and all(_equal(a,b) for a,b in zip(left,right))
    return left==right

def _component_matches(name,observed,expected,owner_path,source_path,*,relocated):
    if observed.keys()!=expected.keys():return False
    for field,value in expected.items():
        if relocated and name=='DefaultSceneRoot' and field.startswith('Relative'):continue
        left,right=_normalize(observed[field]),_normalize(value)
        if field=='AttachParent':
            if left is not None:
                if not isinstance(left,str) or not left.startswith(owner_path+'.'):return False
                left=left[len(owner_path):]
            if right is not None:
                if not isinstance(right,str) or not right.startswith(source_path+'.'):return False
                right=right[len(source_path):]
        if field=='OverrideMaterials':
            while left and left[-1] is None:left.pop()
            while right and right[-1] is None:right.pop()
        if not _equal(left,right):return False
    return True

def _validate_profile(profile):
    if (profile.get('kind')!='sirene_source_v190' or profile.get('source_world')!=SOURCE_WORLD or
        profile.get('source_actor')!=SOURCE_ACTOR or profile.get('helper_class')!=HELPER):
        raise ValueError('Exact retained Sirene source required')
    nodes=profile.get('components',[])
    if len(nodes)!=16 or {n.get('name') for n in nodes}!=NODES:raise ValueError('Exact sixteen source nodes required')
    expected={r['name']:r for r in nodes}
    for name in ('Body','Hair_Sirene_Axon_skl'):
        if expected[name]['class_path']!='/Script/Engine.SkeletalMeshComponent':raise ValueError('Original skeletal class required')
    body=expected['Body']['values']
    if body['AnimationMode']!=0:raise ValueError('Only observed Blueprint animation is supported')
    material_slots=[]
    for name in ('Body','Hair_Sirene_Axon_skl'):
        slots=_normalize(expected[name]['values']['OverrideMaterials'])
        material_slots.extend((name,i) for i,path in enumerate(slots) if path is not None)
    if material_slots!=[('Body',5),('Hair_Sirene_Axon_skl',0)]:raise ValueError('Unexpected material correction set')
    return expected

def prepare_source_presentation(scope,owner,profile,report):
    """One attempt on an inert owned helper; retain all dependencies on failure."""
    expected=_validate_profile(profile)
    if report:raise RuntimeError('Presentation setup is never replayed')
    if owner.actor_identity is None or not owner.has_native_work:raise RuntimeError('Owned helper required')
    report.update(phase='preparing',attempted=True,operations=[],verified=False)
    identity=owner.actor_identity;context=controller_context(scope._session)
    world=load_generated_world(scope,SOURCE_WORLD).return_value
    if world is None:raise RuntimeError('Retained source World unavailable')
    report['source_world_identity']=_identity(world)
    def batch():return ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable)
    def read(c,obj,fields):
        values,c=read_values_with_references(c,obj,fields=fields)
        if values.errors:raise RuntimeError(str(values.errors))
        return {k[1]:v for k,v in values.values.items()},c
    def components(c,actor):
        property_names=tuple(n for n,row in expected.items() if row['property'])
        found,c=read(c,actor,property_names)
        generated=tuple(n for n,row in expected.items() if not row['property'])
        c=c.with_observations(capture_matching(scope.pid,names=generated+('Scene_Attach_Spline',)))
        path=c.path_name(actor)
        for name in generated:
            rows=[o for o in c.objects if c.path_name(o)==path+'.'+name]
            if len(rows)!=1:raise RuntimeError('Generated source node missing or ambiguous: '+name)
            found[name]=rows[0]
        for name,obj in found.items():
            if obj is None or obj.outer_index!=actor.index or c.path_name(c.by_index[obj.class_index])!=expected[name]['class_path']:
                raise RuntimeError('Presentation component ownership/class differs: '+name)
        return found,c
    with batch():
        c=capture_matching(scope.pid,names=(SOURCE_ACTOR.rsplit('.',1)[-1],))
        c=c.with_observations(capture_selected(scope.pid,(_identity(world),identity)))
        source=[o for o in c.objects if c.path_name(o)==SOURCE_ACTOR]
        if len(source)!=1:raise RuntimeError('Exact retained source helper missing or ambiguous')
        original=source[0]
        if c.path_name(c.by_index[original.class_index])!=HELPER or not any(_identity(o)==_identity(world) for o in c.outer_chain(original)):
            raise RuntimeError('Original source World/class differs')
        source_components,c=components(c,original)
        source_values={}
        for name,obj in source_components.items():
            values,c=read(c,obj,tuple(expected[name]['values']));source_values[name]=values
            copied={k:_copy(v,c) for k,v in values.items()}
            if not _component_matches(name,copied,expected[name]['values'],SOURCE_ACTOR,SOURCE_ACTOR,relocated=False):
                raise RuntimeError('Original source component changed: '+name)
        animation=source_values['Body']['AnimClass']
        if animation is None:raise RuntimeError('Source animation unavailable')
        materials=[]
        for name in ('Body','Hair_Sirene_Axon_skl'):
            actual=source_values[name]['OverrideMaterials']
            for index,path in enumerate(expected[name]['values']['OverrideMaterials']['items']):
                if path is not None:materials.append((name,index,actual.items[index]))
        actor=c.by_index[identity[0]]
        if _identity(actor)!=identity or c.path_name(c.by_index[actor.class_index])!=HELPER:raise RuntimeError('Owned helper changed')
        flags,c=read(c,actor,('bHidden','bActorEnableCollision'))
        if flags!={'bHidden':True,'bActorEnableCollision':False}:raise RuntimeError('Presentation correction requires inert helper')
        targets,c=components(c,actor)
        c=c.with_observations(capture_matching(scope.pid,names=('SetAnimClass','SetAnimationMode','SetMaterial','EAnimationMode')))
        def fn(path):
            rows=[o for o in c.objects if c.path_name(o)==path]
            if len(rows)!=1:raise RuntimeError('Exact typed function unavailable: '+path)
            return rows[0]
        fn('/Script/Engine.EAnimationMode')
        planner=scope.invocation_planner(catalog=c,selected_results=True)
        try:
            calls=[('Body.AnimClass',planner.prepare(targets['Body'],fn('/Script/Engine.SkeletalMeshComponent:SetAnimClass'),NewClass=animation)),
                ('Body.AnimationMode',planner.prepare(targets['Body'],fn('/Script/Engine.SkeletalMeshComponent:SetAnimationMode'),InAnimationMode=0,bForceInitAnimScriptInstance=False))]
            calls.extend((f'{name}.Material{index}',planner.prepare(targets[name],fn('/Script/Engine.PrimitiveComponent:SetMaterial'),ElementIndex=index,Material=asset)) for name,index,asset in materials)
            for name,call in calls:
                if owner.actor_identity!=identity or not owner.has_native_work or controller_context(scope._session)!=context:
                    raise RuntimeError('Owner/context changed before source correction')
                operation=dict(field=name,phase='dispatch_intent');report['operations'].append(operation)
                with call.invoke() as result:
                    if result.outcome!='dispatch_returned':raise RuntimeError('Presentation dispatch incomplete; never replay')
                    operation['phase']='dispatch_returned'
        finally:planner.close()
    with batch():
        c=capture_selected(scope.pid,(identity,));actor=c.by_index[identity[0]]
        if _identity(actor)!=identity or owner.actor_identity!=identity or not owner.has_native_work:
            raise RuntimeError('Owned helper replaced before readback')
        targets,c=components(c,actor);path=c.path_name(actor)
        for name,obj in targets.items():
            values,c=read(c,obj,tuple(expected[name]['values']))
            if not _component_matches(name,{k:_copy(v,c) for k,v in values.items()},expected[name]['values'],path,SOURCE_ACTOR,relocated=True):
                raise RuntimeError('Owned presentation differs from retained source: '+name)
    if controller_context(scope._session)!=context:raise RuntimeError('Context changed during source correction')
    report.update(phase='verified',verified=True,components_verified=16)
