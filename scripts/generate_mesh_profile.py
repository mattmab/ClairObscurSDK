"""Generate the fixed prototype's schema checks from recorded target reflection."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'dist/mesh-feasibility'
FUNCTIONS=('GameplayStatics.BeginDeferredActorSpawnFromClass','GameplayStatics.FinishSpawningActor',
 'Actor.AddComponentByClass','Actor.FinishAddComponent','ProceduralMeshComponent.CreateMeshSection_LinearColor',
 'Actor.K2_DestroyActor','Actor.K2_GetActorLocation','Actor.GetActorForwardVector',
 'Actor.SetActorEnableCollision','SceneComponent.SetMobility','ProceduralMeshComponent.GetNumSections','Actor.IsActorBeingDestroyed',
 'PrimitiveComponent.CreateDynamicMaterialInstance','MaterialInstanceDynamic.SetTextureParameterValue',
 'MaterialInstanceDynamic.K2_GetTextureParameterValue','KismetStringLibrary.Conv_StringToName','KismetRenderingLibrary.ImportFileAsTexture2D','KismetSystemLibrary.LineTraceSingle','GameplayStatics.BreakHitResult','MaterialInstanceDynamic.SetVectorParameterValue','SkinnedMeshComponent.GetNumBones','SkinnedMeshComponent.GetBoneName','SkinnedMeshComponent.GetRefPoseTransform','SkinnedMeshComponent.GetBoneTransform','SkinnedMeshComponent.GetParentBone','ProceduralMeshComponent.UpdateMeshSection_LinearColor','SceneComponent.SetHiddenInGame','Pawn.IsPlayerControlled','ActorComponent.GetOwner','SkinnedMeshComponent.GetBoneIndex')
def fields(rows):
    result=[]
    for p in rows:
        result.append('{'+','.join((json.dumps(p['name']),json.dumps(p['type']),str(p['offset']),str(p['element_size']),
            p['flags']+'ULL',p['vtable_rva']+'ULL',json.dumps(p.get('struct_name','')),
            json.dumps(p.get('inner_type','')),str(p.get('inner_element_size',0)),json.dumps(p.get('inner_struct_name','')),
            p.get('bool_encoding','0')+'U',json.dumps(p.get('property_class_name',p.get('meta_class_name','')))))+'}')
    return ',\n'.join(result)
out=['// Generated from the exact shipping-build observations in dist/mesh-feasibility.\n#pragma once']
out+=['struct MeshField {const char* name;const char* type;int offset,width;uint64_t flags,table;const char* structure;const char* inner;int inner_width;const char* inner_structure;uint32_t boolean;const char* constraint;};']
for index,name in enumerate(FUNCTIONS):
    rows=[json.loads(line) for line in (SOURCE/(name+'.jsonl')).read_text().splitlines()]
    props=[p for p in rows if p['event']=='property_metadata']
    if props:out.append(f'inline const MeshField mesh_fields_{index}[]={{'+fields(props)+'};')
out.append('struct MeshFunction {const char* owner;const char* name;uint32_t flags,params,extent,returned;uint64_t entry;const MeshField* fields;size_t count;};')
out.append('inline const MeshFunction mesh_functions[]={')
for index,name in enumerate(FUNCTIONS):
    rows=[json.loads(line) for line in (SOURCE/(name+'.jsonl')).read_text().splitlines()]
    f=next(r for r in rows if r['event']=='function_metadata');s=next(r for r in rows if r['event']=='struct_metadata')
    count=sum(r['event']=='property_metadata' for r in rows)
    out.append('{'+','.join((json.dumps(f['owner']),json.dumps(name.split('.')[1]),f['flags'],str(f['params_size']),str(s['size']),str(f['return_offset']),f['entry_rva'],f'mesh_fields_{index}' if count else 'nullptr',str(count)))+'},')
out.append('};')
rows=[json.loads(line) for line in (SOURCE/'mesh-structs.jsonl').read_text().splitlines()]
for name in ('Transform','Quat'):
    out.append(f'inline const MeshField mesh_{name}[]={{'+fields([p for p in rows if p['event']=='property_metadata' and p['owner']==name])+'};')
(ROOT/'native/mesh_profile.h').write_text('\n'.join(out)+'\n')
