"""Copied assembly evidence through existing scoped SDK reads and class loading.

No actor spawning, animation playback, discovery scan or catalog promotion.
Stored observations are not leases or proof of complete assembly.
"""
import re
from . import RuntimeQueryError
from ._scope import SessionScope
from ._reader import ReadBatch
from .catalog import capture_matching
from .picto_class_load import load_class
from .values import read_values_with_references,StoredArray,StoredStruct

COMPONENT_FIELDS=('SkinnedAsset','AnimClass','AnimationData','AnimationMode',
    'RelativeLocation','RelativeRotation','RelativeScale3D','AttachParent',
    'AttachSocketName','OverrideMaterials')
SCS_FIELDS=('ComponentTemplate','ChildNodes','ParentComponentOrVariableName',
    'ParentComponentOwnerClassName','AttachToName','bIsParentComponentNative')
SCENE_FIELDS=('AttachParent','AttachSocketName','RelativeLocation','RelativeRotation',
    'RelativeScale3D','bHiddenInGame','bVisible')


def _validate_class_path(class_path):
    if type(class_path) is not str or not re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.(?i:\1)_C',class_path):
        raise ValueError('Expected an exact generated game class asset path')


def _belongs_to_templates(catalog,obj,class_indices,default_indices):
    """Exact outer-chain membership; names and path substrings are not evidence."""
    seen=set()
    current=obj
    while current is not None and len(seen)<128:
        if current.index in seen:return False
        seen.add(current.index)
        if current.index in class_indices or current.index in default_indices:return True
        current=catalog.by_index.get(current.outer_index)
    return False


def inspect_loaded_hierarchy(scope,class_path):
    """Copy loaded original templates and SCS edges without loading or spawning.

    Ancestor templates remain explicitly inherited: an inherited mannequin mesh
    is not proof of the derived character's final body. Construction scripts,
    inherited component overrides and runtime setup are not executed here.
    """
    scope._check();_validate_class_path(class_path)
    report={}
    try:
        return _inspect_loaded_hierarchy(scope,class_path,report)
    except RuntimeQueryError as error:
        # A fatal read can close the active worker. Preserve copied evidence and
        # stop rather than issuing more queries or reporting the class unloaded.
        report.setdefault('errors',[]).append(dict(error=str(error),
            phase=report.get('read_phase','initial_discovery')))
        report['status']='partial_read_failed'
        return report


def _incomplete(value):
    if isinstance(value,StoredArray):
        return value.length>len(value.items) or any(_incomplete(v) for v in value.items)
    if isinstance(value,StoredStruct):
        return value.truncated or any(_incomplete(v) for v in value.fields.values())
    return False


def _inspect_loaded_hierarchy(scope,class_path,report):
    report.update(dict(class_path=class_path,read_only=True,class_load_requested=False,
        actor_spawned=False,assembly_verified=False,animation_preview_verified=False,
        components=[],scs_nodes=[],class_templates=[],class_defaults=[],construction_scripts=[],errors=[],truncated=False,
        limitations=['Loaded templates only; construction scripts are not executed.',
            'Inherited templates may be overridden; final assembly is unverified.',
            'Null attachment parents require SCS or runtime evidence; no parent is inferred.',
            'Skeleton compatibility and animation playback require separate evidence.']))
    name=class_path.rsplit('.',1)[-1]
    with ReadBatch(scope.pid):
        try:
            catalog=capture_matching(scope.pid,names=(name,'Default__'+name))
        except RuntimeQueryError as error:
            if '"message":"MATCH_RESULTS_EMPTY"' not in str(error):raise
            report['status']='class_not_observed';return report
        targets=[o for o in catalog.objects if catalog.path_name(o)==class_path]
        if len(targets)!=1:
            report['status']='class_not_observed' if not targets else 'class_ambiguous';return report
        target=targets[0]
        ancestors=set(catalog.ancestors(target.index))
        report['class_ancestry']=[catalog.path_name(catalog.by_index[i]) for i in catalog.ancestors(target.index)]
        # Follow bounded original references instead of enumerating every scene
        # component in the world (which can exceed the reader match limit).
        for index in catalog.ancestors(target.index):
            cls=catalog.by_index[index]
            if not catalog.path_name(cls).startswith('/Game/'):continue
            report['read_phase']='class_templates:'+catalog.path_name(cls)
            values,catalog=read_values_with_references(catalog,cls,fields=(
                'SimpleConstructionScript','ComponentTemplates','InheritableComponentHandler'))
            report['class_templates'].append(_observation(cls,values,catalog))
            if any(_incomplete(v) for v in values.values.values()):report['truncated']=True
            for key,value in values.values.items():
                if key[1]!='SimpleConstructionScript' or value is None:continue
                report['read_phase']='construction_script:'+catalog.path_name(value)
                nodes,catalog=read_values_with_references(catalog,value,fields=('AllNodes','RootNodes'))
                report['construction_scripts'].append(_observation(value,nodes,catalog))
                if any(_incomplete(v) for v in nodes.values.values()):report['truncated']=True
        # The native Character.Mesh subobject is not necessarily an SCS node.
        default_names=tuple('Default__'+catalog.by_index[i].name for i in catalog.ancestors(target.index)
            if catalog.path_name(catalog.by_index[i]).startswith('/Game/'))
        if default_names:
            report['read_phase']='class_defaults_discovery'
            catalog=catalog.with_observations(capture_matching(scope.pid,names=default_names))
        defaults={o.index for o in catalog.objects if o.object_flags&0x10 and o.class_index in ancestors}
        for index in sorted(defaults):
            default=catalog.by_index[index]
            names={catalog.classes[i].name for i in catalog.ancestors(default.class_index)}
            if 'Character' in names:
                report['read_phase']='class_default:'+catalog.path_name(default)
                values,catalog=read_values_with_references(catalog,default,fields=('Mesh',))
                report['class_defaults'].append(_observation(default,values,catalog))
        scoped=[o for o in catalog.objects if _belongs_to_templates(catalog,o,ancestors,defaults)]
        seen=set()
        def read(obj,fields,bucket):
            nonlocal catalog
            identity=(obj.index,obj.serial,obj.address)
            if identity in seen:return None
            if len(report[bucket])>=256:report['truncated']=True;return None
            seen.add(identity)
            try:
                report['read_phase']=bucket+':'+catalog.path_name(obj)
                values,catalog=read_values_with_references(catalog,obj,fields=fields)
                if any(_incomplete(v) for v in values.values.values()):report['truncated']=True
                row=_observation(obj,values,catalog)
                row['class_path']=catalog.path_name(catalog.by_index[obj.class_index])
                # Find the owning class or CDO using the same exact outer chain.
                cursor=obj;visited=set();owner=None
                while cursor is not None and cursor.index not in visited:
                    visited.add(cursor.index)
                    if cursor.index in ancestors:owner=cursor.index;break
                    if cursor.index in defaults:owner=cursor.class_index;break
                    cursor=catalog.by_index.get(cursor.outer_index)
                row['owner_class']=catalog.path_name(catalog.by_index[owner]) if owner is not None else None
                row['inherited']=owner!=target.index if owner is not None else None
                report[bucket].append(row)
                return values
            except RuntimeQueryError:
                raise
        templates=[]
        nodes=[obj for obj in scoped if obj.class_name=='SCS_Node']
        for obj in nodes:
            values=read(obj,SCS_FIELDS,'scs_nodes')
            if values is not None:
                for key,value in values.values.items():
                    if key[1]=='ComponentTemplate' and value is not None:templates.append(value)
                    if key[1]=='ChildNodes' and isinstance(value,StoredArray):
                        for child in value.items:
                            if child is not None and child.index not in {n.index for n in nodes}:
                                if len(nodes)>=256:report['truncated']=True;break
                                if _belongs_to_templates(catalog,child,ancestors,defaults):nodes.append(child)
        # Derived Blueprint overrides of an inherited SCS template are not
        # necessarily enumerated by ComponentTemplates or their own SCS nodes.
        # Discover the exact names from actual SCS references, then constrain
        # matches by original class/default ownership before reading them.
        template_names=tuple(sorted({obj.name for obj in templates}))
        if template_names:
            report['read_phase']='inherited_component_overrides'
            if len(template_names)>256:
                report['truncated']=True
                report['errors'].append(dict(phase=report['read_phase'],error='Template name bound exceeded'))
            else:
                catalog=catalog.with_observations(capture_matching(scope.pid,names=template_names))
                scoped=[obj for obj in catalog.objects if _belongs_to_templates(catalog,obj,ancestors,defaults)]
                report['override_template_names']=list(template_names)
        for obj in (*scoped,*templates):
            lineage={catalog.classes[i].name for i in catalog.ancestors(obj.class_index)}
            if 'ActorComponent' not in lineage:continue
            if 'SkeletalMeshComponent' in lineage:fields=(*COMPONENT_FIELDS,'LeaderPoseComponent','bHiddenInGame','bVisible')
            elif 'StaticMeshComponent' in lineage:fields=('StaticMesh',*SCENE_FIELDS,'OverrideMaterials')
            elif 'ChildActorComponent' in lineage:fields=('ChildActorClass','ChildActor',*SCENE_FIELDS)
            elif 'SceneComponent' in lineage:fields=SCENE_FIELDS
            else:fields=('LinkedDummyCharacterClass',)
            read(obj,fields,'components')
        report['status']='templates_observed'
        report.pop('read_phase',None)
    return report


def _copy(value,catalog):
    if hasattr(value,'class_index'):
        return catalog.path_name(value)
    if isinstance(value,StoredStruct):
        return {'fields':{key:_copy(v,catalog) for key,v in value.fields.items()},
            'errors':{key:str(v) for key,v in value.errors.items()},'truncated':value.truncated}
    if isinstance(value,StoredArray):
        return {'length':value.length,'items':[_copy(v,catalog) for v in value.items]}
    if isinstance(value,(list,tuple)):
        return [_copy(v,catalog) for v in value]
    return value


def _observation(obj,values,catalog):
    return {'source_path':catalog.path_name(obj),
        'values':{key[1]:_copy(value,catalog) for key,value in values.values.items()},
        'errors':{key[1]:str(value) for key,value in values.errors.items()}}


def inspect_class(scope,class_path,*,load=False,include_hierarchy=False):
    scope._check()
    if type(load) is not bool:raise ValueError('Class-loading choice must be bool')
    if type(include_hierarchy) is not bool:raise ValueError('Hierarchy inspection choice must be bool')
    _validate_class_path(class_path)
    child=SessionScope(scope)
    report={'class_path':class_path,'class_load_requested':load,'actor_spawned':False,
        'assembly_verified':False,'animation_preview_verified':False,
        'limitation':'Character.Mesh only; additional SCS components and construction behavior are not complete.'}
    if include_hierarchy:report['limitation']='Original native mesh and loaded SCS templates; construction behavior and inherited overrides remain unverified.'
    try:
        retained=load_class(child,class_path) if load else None
        if include_hierarchy:report['hierarchy']=inspect_loaded_hierarchy(scope,class_path)
        with ReadBatch(scope.pid):
            try:
                catalog=capture_matching(scope.pid,names=('Default__'+class_path.rsplit('.',1)[-1],))
            except RuntimeQueryError as error:
                if '"message":"MATCH_RESULTS_EMPTY"' not in str(error):raise
                report['status']='default_not_observed'
                return report
            defaults=[o for o in catalog.objects if o.object_flags&0x10 and o.class_index in catalog.by_index
                and catalog.path_name(catalog.by_index[o.class_index])==class_path]
            if len(defaults)!=1:raise RuntimeError('Missing or ambiguous original class default')
            obj=defaults[0]
            if retained is not None:
                observed=catalog.by_index[obj.class_index];expected=retained.return_value
                if (observed.index,observed.serial,observed.address)!=(expected.index,expected.serial,expected.address):
                    raise RuntimeError('Loaded class differs from observed default owner')
            values,catalog=read_values_with_references(catalog,obj,fields=('Mesh',))
            report['default']=_observation(obj,values,catalog)
            mesh=next((v for key,v in values.values.items() if key[1]=='Mesh'),None)
            if mesh is None:
                report['status']='native_mesh_missing_or_unreadable'
                return report
            values,catalog=read_values_with_references(catalog,mesh,fields=COMPONENT_FIELDS)
            report['native_mesh_component']=_observation(mesh,values,catalog)
            report['status']='native_mesh_observed'
            return report
    except RuntimeQueryError as error:
        if not include_hierarchy:raise
        report['status']='partial_native_mesh_read_failed'
        report['error']=str(error)
        return report
    finally:
        child.close()
