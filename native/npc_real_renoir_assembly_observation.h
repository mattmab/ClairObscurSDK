#pragma once
#include "npc_clea_assembly_observation.h"

namespace e33_npc_presentation {
// Read-only expectations from the original NoInteract CDO, inherited SCS and
// exact engine schema. This observer alone grants no staging/entry authority.
inline bool real_renoir_material(uint64_t b,uint64_t component,const char* name,const char* package){
    const auto materials=component_field(b,component,"OverrideMaterials","ArrayProperty",1304,16,
        "MeshComponent",0x6e0de80,0x114040000000201ULL);
    uint64_t descriptor=0;
    if(!materials||!picto_field(b,component,"OverrideMaterials","ArrayProperty",1304,16,&descriptor)||
       !descriptor||(local_read<uint8_t>(descriptor+0x70)&1))return false;
    const auto inner=local_read<uint64_t>(descriptor+0x78);
    if(!inner||local_read<uint64_t>(inner)!=b+0x6e11d38||local_read<uint64_t>(inner+16)!=descriptor||
       local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=8)return false;
    const auto data=local_read<uint64_t>(materials);
    const auto count=local_read<int32_t>(materials+8),capacity=local_read<int32_t>(materials+12);
    return count==1&&capacity>=count&&capacity<=1024&&data>=0x10000&&!(data&7)&&
        e33_mesh::candidate_named(b,local_read<uint64_t>(data),name,package);
}
inline bool real_renoir_pose(const CleaComponentObservation& pose,const double* location,
        const double* rotation,const double* scale){
    for(unsigned i=0;i<3;++i)if(!std::isfinite(pose.location[i])||!std::isfinite(pose.rotation[i])||
        !std::isfinite(pose.scale[i])||std::abs(pose.location[i]-location[i])>0.0001||
        std::abs(pose.rotation[i]-rotation[i])>0.0001||std::abs(pose.scale[i]-scale[i])>0.0001)return false;
    return true;
}
inline bool real_renoir_static_pose(uint64_t b,uint64_t component,CleaComponentObservation& out){
    out={};out.component=call_capture(b,component);
    if(!call_identity(b,out.component))return false;
    const auto parent=component_field(b,component,"AttachParent","ObjectProperty",176,8,"SceneComponent",0x6e11d38,0x14c001100080228ULL);
    const auto socket=component_field(b,component,"AttachSocketName","NameProperty",184,8,"SceneComponent",0x6e13040,0x48001140000220ULL);
    const auto location=component_field(b,component,"RelativeLocation","StructProperty",296,24,"SceneComponent",0x6e136a0,0x48001140000235ULL);
    const auto rotation=component_field(b,component,"RelativeRotation","StructProperty",320,24,"SceneComponent",0x6e136a0,0x40001140000235ULL);
    const auto scale=component_field(b,component,"RelativeScale3D","StructProperty",344,24,"SceneComponent",0x6e136a0,0x48001140000235ULL);
    if(!parent||!socket||!location||!rotation||!scale)return false;
    out.parent=local_read<uint64_t>(parent);out.socket=local_read<uint64_t>(socket);
    std::memcpy(out.location,reinterpret_cast<const void*>(location),24);
    std::memcpy(out.rotation,reinterpret_cast<const void*>(rotation),24);
    std::memcpy(out.scale,reinterpret_cast<const void*>(scale),24);
    return true;
}
inline bool observe_real_renoir_assembly(uint64_t b,CallIdentity actor,CallIdentity cls,CallIdentity cdo,
        CallIdentity available,CleaAssemblyObservation& out){
    out={};
    if(!TargetPodSchemaOps{b}.context()||!original_class_contract(b,cls,cdo,available)||
       !e33_mesh::named(b,cls.address,"BP_JRPG_NPC_Dialog_NPC_RealRenoir_NoInteract_C",
           "/Game/Characters/Enemies/HumanEnnemies/Real_Renoir/BP_JRPG_NPC_Dialog_NPC_RealRenoir_NoInteract")||
       !call_identity(b,actor)||local_read<uint64_t>(actor.address+16)!=cls.address||
       (local_read<uint32_t>(actor.address+8)&0x30))return false;
    const auto mesh=picto_field(b,actor.address,"Mesh","ObjectProperty",792,8);
    const auto capsule=picto_field(b,actor.address,"CapsuleComponent","ObjectProperty",808,8);
    if(!mesh||!capsule)return false;
    const auto body=local_read<uint64_t>(mesh),root=local_read<uint64_t>(capsule);
    uint64_t indicator_descriptor=0;
    const auto indicator_field=picto_field(b,actor.address,"PlayerLocationIndicator","ObjectProperty",1848,8,&indicator_descriptor);
    if(!indicator_field||!indicator_descriptor||local_read<uint64_t>(indicator_descriptor)!=b+0x6e11d38||
       local_read<uint64_t>(indicator_descriptor+0x38)!=0x8001400080204ULL||
       !e33_mesh::named(b,local_read<uint64_t>(indicator_descriptor+16)&~uint64_t(1),"BP_jRPG_NPC_Dialog_C","/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog")||
       !e33_mesh::named(b,local_read<uint64_t>(indicator_descriptor+0x70),"StaticMeshComponent","/Script/Engine"))return false;
    const auto indicator=local_read<uint64_t>(indicator_field);
    CleaComponentObservation cane{};unsigned cane_count=0,indicator_count=0,unexpected_static=0;
    auto inspect=[&](uint64_t component){
        if(!call_identity(b,call_capture(b,component))||local_read<uint64_t>(component+32)!=actor.address)return false;
        const auto skinned=picto_field(b,component,"SkinnedAsset","ObjectProperty",1384,8);
        if(skinned){
            if(!component_field(b,component,"SkinnedAsset","ObjectProperty",1384,8,"SkinnedMeshComponent",0x6e11d38,0x14c001000000214ULL))return false;
            const auto asset=local_read<uint64_t>(skinned);if(!asset)return true;
            const auto animation=component_field(b,component,"AnimClass","ClassProperty",2248,8,"SkeletalMeshComponent",0x6e12ac8,0x1c001000000215ULL);
            if(!animation)return false;
            CleaComponentObservation* selected=nullptr;
            if(e33_mesh::named(b,asset,"SK_Real_Renoir_UE5","/Game/Characters/Enemies/HumanEnnemies/Real_Renoir/SK_Real_Renoir_UE5")){
                if(++out.body_count!=1||component!=body||!e33_mesh::named(b,local_read<uint64_t>(animation),"ABP_Noah_NPC_C","/Game/Characters/Heros/Camps/ABP_Noah_NPC"))return false;
                out.body_material=real_renoir_material(b,component,"MI_Body_NPC_Man_Peach","/Game/Characters/NPCs/Lumiere/Body/Material/MI_Body_NPC_Man_Peach");selected=&out.body;
            }else if(e33_mesh::named(b,asset,"Renoir_v2_FaceMesh","/Game/MetaHumans/Renoir_v2/Face/Renoir_v2_FaceMesh")){
                if(++out.face_count!=1||!e33_mesh::named(b,local_read<uint64_t>(animation),"Face_NPCSimple_AnimBP_C","/Game/Characters/NPCs/Face_NPCSimple_AnimBP"))return false;
                selected=&out.face;
            }else if(e33_mesh::named(b,asset,"Renoir_Hair_RealRenoir_sk","/Game/Characters/Hair/Mirror_Family/Renoir/Renoir_Hair_RealRenoir_sk")){
                if(++out.hair_count!=1||local_read<uint64_t>(animation))return false;selected=&out.hair;
            }else{++out.unexpected_skinned_assets;return true;}
            return observe_clea_component(b,component,*selected);
        }
        const auto static_mesh=picto_field(b,component,"StaticMesh","ObjectProperty",1376,8);
        if(!static_mesh)return true;
        if(!component_field(b,component,"StaticMesh","ObjectProperty",1376,8,"StaticMeshComponent",0x6e11d38,0x14c001100000235ULL))return false;
        const auto asset=local_read<uint64_t>(static_mesh);if(!asset)return true;
        if(component==indicator&&e33_mesh::named(b,asset,"Mannequin","/Game/Meshes/Mannequin")){
            // Original hidden placement indicator, not another visible body.
            uint64_t hidden_descriptor=0;
            const auto hidden=component_field(b,component,"bHiddenInGame","BoolProperty",393,1,"SceneComponent",0x6e119b0,0x18001200000015ULL);
            if(!hidden||!picto_field(b,component,"bHiddenInGame","BoolProperty",393,1,&hidden_descriptor)||
               !hidden_descriptor||local_read<uint32_t>(hidden_descriptor+0x70)!=0x08080001U||!(local_read<uint8_t>(hidden)&8))return false;
            return ++indicator_count==1;
        }
        if(!e33_mesh::named(b,asset,"renoir_cane","/Game/Characters/Enemies/HumanEnnemies/Mirror_Renoir/renoir_cane")){++unexpected_static;return true;}
        return ++cane_count==1&&real_renoir_material(b,component,"M_Corrupted_Inst","/Game/FX/FX_Leo/Materials/M_Corrupted_Inst")&&real_renoir_static_pose(b,component,cane);
    };
    if(!body||!root||!call_identity(b,call_capture(b,root))||local_read<uint64_t>(root+32)!=actor.address||
       !inspect(body)||!e33_owned_actor::visit_components(b,actor.address,[&](uint64_t component){return component==body||inspect(component);}))return false;
    const double zero[]={0,0,0},unit[]={1,1,1},body_location[]={0,0,-88},body_rotation[]={0,-90,0};
    const double hair_location[]={8.010332,-1.052621,-0.000029},hair_rotation[]={-90,-0.000007,0.000072};
    return out.body_count==1&&out.face_count==1&&out.hair_count==1&&!out.unexpected_skinned_assets&&out.body_material&&
        cane_count==1&&indicator_count==1&&!unexpected_static&&out.body.parent==root&&out.face.parent==body&&
        out.hair.parent==out.face.component.address&&cane.parent==body&&
        exact_name(b,reinterpret_cast<uint64_t>(&out.face.socket),"None")&&
        exact_name(b,reinterpret_cast<uint64_t>(&out.hair.socket),"Head")&&
        exact_name(b,reinterpret_cast<uint64_t>(&cane.socket),"weapon_l")&&
        real_renoir_pose(out.body,body_location,body_rotation,unit)&&real_renoir_pose(out.face,zero,zero,unit)&&
        real_renoir_pose(out.hair,hair_location,hair_rotation,unit)&&real_renoir_pose(cane,zero,zero,unit)&&call_identity(b,actor);
}
}
