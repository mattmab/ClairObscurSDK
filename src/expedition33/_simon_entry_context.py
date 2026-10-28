"""Conservative original Simon entry-area preflight, observation only.

This admits the original boss trigger's authored sphere, not every position from
which a cinematic might render correctly. It never teleports the player, moves
the trigger, changes lighting, or infers cinematic visibility from proximity.
This optional research qualification is separate from the encounter adapter; it
intentionally rejects some positions where the phase cinematic visibly works.
"""
from dataclasses import dataclass
import math

from . import simon_source
from ._reader import ReadBatch, active_reader
from ._world_level_membership import observe_actor_membership
from .catalog import capture_matching, capture_selected
from .cinematics.history import field, identity
from .cinematics.original_game_action import controller_context
from .values import StoredArray, StoredStruct, read_values_with_references

ZONE_NAME='BP_GameActionTriggerZone_C_UAID_C87F5409F1EC9BF501_1262586402'
ZONE_PATH=simon_source.WORLD+':PersistentLevel.'+ZONE_NAME
ZONE_CLASS='/Game/LevelTools/MovementZone/BP_GameActionTriggerZone.BP_GameActionTriggerZone_C'
ROOT_LOCATION=(20899.25153426259,7729.147232835192,-402292.0046773091)
ROOT_ROTATION=(0.,17.85949851994406,0.)
SPHERE_LOCATION=(118.49445802638598,-4.9840227236579455,0.)
SPHERE_ROTATION=(0.,-20.126026293037803,0.)
SPHERE_SCALE=(87.16781616210938,84.49947357177734,43.969600677490234)
SPHERE_RADIUS=32.
ENTRY_POLICY='conservative_authored_trigger_sphere'


class SimonEntryNotReady(RuntimeError):
    pass


@dataclass(frozen=True)
class SimonEntryObservation:
    pawn: tuple
    zone: tuple
    sphere: tuple
    position: tuple
    center: tuple
    radius: float
    policy: str=ENTRY_POLICY


def _read(catalog,obj,names):
    observed,catalog=read_values_with_references(catalog,obj,fields=tuple(names))
    return {name:field(observed,name,kind) for name,kind in names.items()},catalog


def _live(obj):
    if obj is None or obj.object_flags&0x40000030 or getattr(obj,'item_flags',0)&0x200000:
        raise SimonEntryNotReady('Original Simon entry object is missing, a template or retiring')


def _vector(catalog,value,*,rotation=False):
    names=('Pitch','Yaw','Roll') if rotation else ('X','Y','Z')
    path='/Script/CoreUObject.'+('Rotator' if rotation else 'Vector')
    if (not isinstance(value,StoredStruct) or value.errors or value.truncated or
            catalog.path_name(catalog.resolve(value.type_object))!=path or set(value.fields)!=set(names) or
            any(value.types.get(name)!='DoubleProperty' for name in names)):
        raise SimonEntryNotReady('Complete exact Simon entry Vector/Rotator observation required')
    result=tuple(value.fields[name] for name in names)
    if any(type(number) not in (int,float) or not math.isfinite(number) or abs(number)>1e7 for number in result):
        raise SimonEntryNotReady('Finite bounded Simon entry frame required')
    return result


def _same(actual,expected):
    return len(actual)==len(expected) and all(abs(a-b)<=.0001 for a,b in zip(actual,expected))


def _frame(catalog,component):
    values,catalog=_read(catalog,component,{'RelativeLocation':'StructProperty',
        'RelativeRotation':'StructProperty','RelativeScale3D':'StructProperty','AttachParent':'ObjectProperty'})
    return (_vector(catalog,values['RelativeLocation']),_vector(catalog,values['RelativeRotation'],rotation=True),
            _vector(catalog,values['RelativeScale3D']),values['AttachParent']),catalog


def require_inside(position):
    """Conservative copied-point check; no gameplay or visibility assertion."""
    position=tuple(position)
    if len(position)!=3 or any(type(n) not in (int,float) or not math.isfinite(n) or abs(n)>1e7 for n in position):
        raise ValueError('Finite bounded exploration position required')
    yaw=math.radians(ROOT_ROTATION[1])
    center=(ROOT_LOCATION[0]+math.cos(yaw)*SPHERE_LOCATION[0]-math.sin(yaw)*SPHERE_LOCATION[1],
            ROOT_LOCATION[1]+math.sin(yaw)*SPHERE_LOCATION[0]+math.cos(yaw)*SPHERE_LOCATION[1],ROOT_LOCATION[2])
    # Minimum positive source scale gives a conservative sphere contained in the
    # nonuniform source component envelope. No arbitrary working radius is added.
    radius=SPHERE_RADIUS*min(SPHERE_SCALE)
    if math.dist(position,center)>radius:
        raise SimonEntryNotReady('Outside the conservative original Simon entry zone (optional source-context qualification)')
    return center,radius


def require_original_entry(scope,context,*,root):
    """Optionally qualify current pawn/source trigger geometry for research.

    The exact source shape is intentionally narrower than all known working
    positions. Queries are not GC-atomic; native dispatch validation remains
    mandatory. This function owns no native resources and makes no writes.
    """
    scope._check()
    if context['world_path']!=simon_source.WORLD or root.pid!=scope.pid:
        raise SimonEntryNotReady('Exact original Simon world and source required for entry admission')
    with ReadBatch(scope.pid,share=active_reader() is None,_executable=scope._session._transport._executable):
        if controller_context(scope._session,project=True)!=context:
            raise SimonEntryNotReady('Simon entry controller/world changed before observation')
        catalog=capture_matching(scope.pid,names=(ZONE_NAME,))
        zones=[obj for obj in catalog.objects if obj.class_name=='BP_GameActionTriggerZone_C' and
               catalog.path_name(obj)==ZONE_PATH and not obj.object_flags&0x40000030]
        if len(zones)!=1:
            raise SimonEntryNotReady('One exact original Simon boss entry trigger required')
        zone=zones[0]
        if catalog.path_name(catalog.by_index[zone.class_index])!=ZONE_CLASS:
            raise SimonEntryNotReady('Original Simon entry trigger class changed')
        observe_actor_membership(scope,zone,expected_context=context)
        values,catalog=_read(catalog,zone,{'GameActionOnOverlap':'StructProperty','DefaultSceneRoot':'ObjectProperty',
            'TriggerComponents':'ArrayProperty'})
        wrapper=values['GameActionOnOverlap']
        if (not isinstance(wrapper,StoredStruct) or wrapper.errors or wrapper.truncated or
                catalog.path_name(catalog.resolve(wrapper.type_object))!=simon_source.WRAPPER_CLASS or
                set(wrapper.fields)!={'GameActionReference','GameActionInline'} or
                dict(wrapper.types)!={'GameActionReference':'ObjectProperty','GameActionInline':'ObjectProperty'} or
                wrapper.fields['GameActionInline'] is not None or wrapper.fields['GameActionReference'] is None or
                identity(catalog.resolve(wrapper.fields['GameActionReference']))!=identity(root) or
                catalog.path_name(catalog.resolve(root))!=simon_source.ROOT):
            raise SimonEntryNotReady('Original entry trigger does not reference the exact retained Simon graph')
        components=values['TriggerComponents']
        if (not isinstance(components,StoredArray) or components.length!=len(components.items) or
                components.length!=3 or any(obj is None for obj in components.items) or
                len({identity(obj) for obj in components.items})!=3):
            raise SimonEntryNotReady('Complete original Simon entry trigger components required')
        sphere_rows=[obj for obj in components.items if obj.name=='Sphere' and obj.class_name=='SphereComponent']
        if len(sphere_rows)!=1:
            raise SimonEntryNotReady('Exact original Simon trigger sphere required')
        scene,sphere=values['DefaultSceneRoot'],sphere_rows[0]
        for obj,path in ((scene,'/Script/Engine.SceneComponent'),(sphere,'/Script/Engine.SphereComponent')):
            _live(obj)
            if ((obj.outer_index,obj.outer_serial)!=(zone.index,zone.serial) or
                    catalog.path_name(catalog.by_index[obj.class_index])!=path):
                raise SimonEntryNotReady('Original Simon entry component ownership/class changed')
        root_frame,catalog=_frame(catalog,scene)
        sphere_frame,catalog=_frame(catalog,sphere)
        if (not _same(root_frame[0],ROOT_LOCATION) or not _same(root_frame[1],ROOT_ROTATION) or
                not _same(root_frame[2],(1.,1.,1.)) or root_frame[3] is not None or
                not _same(sphere_frame[0],SPHERE_LOCATION) or not _same(sphere_frame[1],SPHERE_ROTATION) or
                not _same(sphere_frame[2],SPHERE_SCALE) or sphere_frame[3] is None or
                identity(sphere_frame[3])!=identity(scene)):
            raise SimonEntryNotReady('Original Simon entry frame differs from its authored source')
        values,catalog=_read(catalog,sphere,{'SphereRadius':'FloatProperty','bGenerateOverlapEvents':'BoolProperty'})
        if (type(values['SphereRadius']) not in (int,float) or values['SphereRadius']!=SPHERE_RADIUS or
                values['bGenerateOverlapEvents'] is not True):
            raise SimonEntryNotReady('Original Simon trigger sphere radius/overlap policy differs')
        catalog=catalog.with_observations(capture_selected(scope.pid,(tuple(context['controller'][1:]),)))
        controller=catalog.by_index[context['controller'][1]]
        values,catalog=_read(catalog,controller,{'Pawn':'ObjectProperty'})
        pawn=values['Pawn'];_live(pawn)
        if pawn.class_name!='BP_jRPG_Character_World_C':
            raise SimonEntryNotReady('Current original Simon exploration pawn required')
        observe_actor_membership(scope,pawn,expected_context=context)
        values,catalog=_read(catalog,pawn,{'RootComponent':'ObjectProperty'})
        pawn_root=values['RootComponent'];_live(pawn_root)
        if (pawn_root.outer_index,pawn_root.outer_serial)!=(pawn.index,pawn.serial):
            raise SimonEntryNotReady('Current exploration pawn root ownership differs')
        pawn_frame,catalog=_frame(catalog,pawn_root)
        if pawn_frame[3] is not None:
            raise SimonEntryNotReady('Unattached exploration pawn root required for original entry admission')
        position=pawn_frame[0]
        center,radius=require_inside(position)
        final_frame,catalog=_frame(catalog,pawn_root)
        if not _same(final_frame[0],position) or final_frame[3] is not None:
            raise SimonEntryNotReady('Exploration pawn moved during original entry observation')
        if controller_context(scope._session,project=True)!=context:
            raise SimonEntryNotReady('Simon entry controller/world changed during observation')
    scope._check()
    return SimonEntryObservation(identity(pawn),identity(zone),identity(sphere),position,center,radius)
