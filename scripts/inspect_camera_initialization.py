"""Read only, inside caller's retained asset scope; no attachment or loading.

Call inspect_retained_camera_template(catalog, assets[0]) from actor_imports
before scope.close(). Supply the fresh full catalog captured while assets are held.
This helper neither pins objects nor authorizes spawning or Play.
"""
import math
from expedition33.catalog import CatalogObject
from expedition33.values import StoredArray, StoredStruct, read_values

SEQUENCE = '/Game/Cinematics/MonolithInterior/Locomotive/CS_GPE_MonolithInterior_Locomotive_MonocoToLumiere.CS_GPE_MonolithInterior_Locomotive_MonocoToLumiere'
CAMERA = 'CineCameraActor_UAID_C87F5450C91E6C9E01_0'
ACTOR_FIELDS = ('CameraComponent','SceneComponent','RootComponent','AutoActivateForPlayer',
 'AutoReceiveInput','bBlockInput','PrimaryActorTick','bActorEnableCollision',
 'LookatTrackingSettings','bAllowTickBeforeBeginPlay','bReplicates','InputComponent',
 'OnActorBeginOverlap','OnActorEndOverlap','OnDestroyed','OnEndPlay')
COMPONENT_FIELDS = ('PrimaryComponentTick','bAutoActivate','bCanEverAffectNavigation',
 'bReplicates','bShouldUpdatePhysicsVolume','bVisible','bHiddenInGame','AttachParent',
 'ComponentVelocity','RelativeLocation','RelativeRotation','PhysicsVolume',
 'PhysicsVolumeChangedDelegate','OnComponentActivated','OnComponentDeactivated')
CAMERA_FIELDS = COMPONENT_FIELDS + ('FocusSettings','bUsePawnControlRotation','bLockToHmd',
 'PostProcessBlendWeight','PostProcessSettings','Filmback','CropSettings','CurrentFocusDistance')

def copied(value, catalog, *, depth=0, budget=None):
    if budget is None: budget=[512]
    budget[0]-=1
    if budget[0]<0 or depth>6: return {'unknown':'report copy bound reached'}
    if isinstance(value,CatalogObject):
        obj=catalog.resolve(value)
        return {'path':catalog.path_name(obj),'pid':obj.pid,'index':obj.index,
                'serial':obj.serial,'class':obj.class_name}
    if isinstance(value,StoredStruct):
        return {'struct':value.type_object.name,'fields':{str(k):copied(v,catalog,depth=depth+1,budget=budget) for k,v in list(value.fields.items())[:64]},
                'errors':{str(k):str(v) for k,v in list(value.errors.items())[:64]},
                'truncated':value.truncated or len(value.fields)>64 or len(value.errors)>64}
    if isinstance(value,StoredArray):
        return {'length':value.length,'items':[copied(v,catalog,depth=depth+1,budget=budget) for v in value.items[:32]],
                'truncated':value.length!=min(len(value.items),32)}
    if value is None or type(value) in (str,int,bool):return value
    if type(value) is float:return value if math.isfinite(value) else {'unknown':'nonfinite number'}
    return {'unknown':'unsupported copied type '+type(value).__name__}

def field(values, name):
    keys=[k for k in set(values.values)|set(values.errors)|set(values.truncated) if k[1]==name]
    if len(keys)!=1:raise ValueError('Missing or ambiguous field '+name)
    key=keys[0]
    if key in values.errors or key in values.truncated or key not in values.values:
        raise ValueError('Unreadable ownership field '+name)
    return values.values[key]

def selected(values, names, catalog):
    result={}
    for name in names:
        keys=[k for k in set(values.values)|set(values.errors)|set(values.truncated) if k[1]==name]
        if len(keys)!=1:result[name]={'unknown':'missing or ambiguous reflected observation'};continue
        key=keys[0]
        row={'owner_index':key[0],'type':values.types.get(key),'truncated':key in values.truncated}
        if key in values.errors:row['unknown']=str(values.errors[key])
        if key in values.values:row['value']=copied(values.values[key],catalog)
        if key not in values.values and key not in values.errors:row['unknown']='no copied value'
        result[name]=row
    return result

def inspect_retained_camera_template(catalog, retained_asset):
    asset=catalog.resolve(retained_asset)
    if asset.class_name!='LevelSequence' or catalog.path_name(asset)!=SEQUENCE:
        raise ValueError('Expected exact retained Locomotive sequence')
    scene=catalog.resolve(field(read_values(catalog,asset),'MovieScene'))
    if scene.class_name!='MovieScene' or (scene.outer_index,scene.outer_serial)!=(asset.index,asset.serial):
        raise ValueError('MovieScene ownership mismatch')
    matches=[o for o in catalog.objects if o.name==CAMERA and o.class_name=='CineCameraActor' and (o.outer_index,o.outer_serial)==(scene.index,scene.serial)]
    if len(matches)!=1:raise ValueError('Expected exactly one native camera template')
    actor=catalog.resolve(matches[0]); av=read_values(catalog,actor)
    camera=catalog.resolve(field(av,'CameraComponent')); root=catalog.resolve(field(av,'SceneComponent'))
    if catalog.resolve(field(av,'RootComponent'))!=root:raise ValueError('Root component changed')
    for obj,name,cls in ((camera,'CameraComponent','CineCameraComponent'),(root,'SceneComponent','SceneComponent')):
        if obj.name!=name or obj.class_name!=cls or (obj.outer_index,obj.outer_serial)!=(actor.index,actor.serial):
            raise ValueError('Exact component ownership mismatch')
    cv=read_values(catalog,camera); rv=read_values(catalog,root)
    if catalog.resolve(field(cv,'AttachParent'))!=root:raise ValueError('Camera attachment mismatch')
    return {'sequence':SEQUENCE,'read_only':True,'spawned':False,
        'scope_requirement':'caller retains sequence throughout these four identity-checked reads',
        'actor':{'identity':copied(actor,catalog),'fields':selected(av,ACTOR_FIELDS,catalog)},
        'camera_component':{'identity':copied(camera,catalog),'fields':selected(cv,CAMERA_FIELDS,catalog)},
        'scene_component':{'identity':copied(root,catalog),'fields':selected(rv,COMPONENT_FIELDS,catalog)},
        'limitations':['Observations are not GC-atomic.','Unsupported, missing and truncated fields remain unknown.','No native constructor or delegate invocation-list proof is claimed.']}
