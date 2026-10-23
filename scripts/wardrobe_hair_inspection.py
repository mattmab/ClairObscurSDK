"""Private, read-only Wardrobe attachment capture for fitting research."""
from expedition33._reader import ReadBatch
from expedition33.catalog import capture_matching,CatalogObject
from expedition33.values import read_values_with_references,StoredStruct,StoredArray
from expedition33.procedural_mesh import capture_bones
from expedition33._scope import SessionScope

def inspect(session):
    scope=SessionScope(session,lease_owner='NativeHairReference')
    try:
        with ReadBatch(session.pid,_executable=session._transport._executable):
            c=capture_matching(session.pid,classes=('BP_GameMenu_Lune_C',))
            actor=next(o for o in c.objects if o.class_name=='BP_GameMenu_Lune_C' and not o.object_flags&0x30)
            v,c=read_values_with_references(c,actor,fields=('Body','Face','MeshesToAlter'))
            values={k[1]:x for k,x in v.values.items()}
            def convert(x):
                if isinstance(x,CatalogObject):return dict(index=x.index,serial=x.serial,path=c.path_name(x),kind=x.class_name)
                if isinstance(x,StoredStruct):return {k:convert(y) for k,y in x.fields.items()}
                if isinstance(x,StoredArray):return [convert(y) for y in x.items]
                return x
            result=[]
            for o in values['MeshesToAlter'].items:
                if not o or o.name in ('Body','Face'):continue
                v,c=read_values_with_references(c,o,fields=('SkinnedAsset','StaticMesh','AttachParent','AttachSocketName','RelativeLocation','RelativeRotation','RelativeScale3D','AnimClass'))
                row=dict(object=convert(o),values={k[1]:convert(x) for k,x in v.values.items()},errors={k[1]:str(x) for k,x in v.errors.items()})
                if o.class_name=='SkeletalMeshComponent':
                    row['bones']=capture_bones(scope,o.index,0)['bones']
                result.append(row)
            return result
    finally:scope.close()
