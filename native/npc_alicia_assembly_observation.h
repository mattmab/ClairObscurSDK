#pragma once
#include "npc_real_renoir_assembly_observation.h"

namespace e33_npc_presentation {
// Exact original Alicia template expectations; no spawning or entry authority.
inline bool alicia_materials(uint64_t b,uint64_t component,int expected,bool face=false){
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
    if(count!=expected||capacity<count||capacity>1024||(count&&(data<0x10000||(data&7))))return false;
    for(int i=0;i<count;++i){
        const auto value=local_read<uint64_t>(data+8*i);
        const bool head=face&&(i==0||i==9||i>=11);
        if(head){
            if(!e33_mesh::candidate_named(b,value,"MI_HeadSynthesized_Baked_Alicia",
                "/Game/Characters/Enemies/HumanEnnemies/Alicia/Face_Texture/MI_HeadSynthesized_Baked_Alicia"))return false;
        }else if(value)return false;
    }
    return true;
}
inline bool observe_alicia_assembly(uint64_t b,CallIdentity actor,CallIdentity cls,CallIdentity cdo,
        CallIdentity available,CleaAssemblyObservation& out){
    out={};
    if(!TargetPodSchemaOps{b}.context()||!original_class_contract(b,cls,cdo,available)||
       !e33_mesh::named(b,cls.address,"BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract_C",
           "/Game/Characters/Enemies/HumanEnnemies/Alicia/BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract")||
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
    CleaComponentObservation mask{},brush{};
    unsigned mask_count=0,brush_count=0,indicator_count=0,unexpected_static=0;
    auto inspect=[&](uint64_t component){
        if(!call_identity(b,call_capture(b,component))||local_read<uint64_t>(component+32)!=actor.address)return false;
        const auto skinned=picto_field(b,component,"SkinnedAsset","ObjectProperty",1384,8);
        if(skinned){
            if(!component_field(b,component,"SkinnedAsset","ObjectProperty",1384,8,"SkinnedMeshComponent",0x6e11d38,0x14c001000000214ULL))return false;
            const auto asset=local_read<uint64_t>(skinned);if(!asset)return true;
            const auto animation=component_field(b,component,"AnimClass","ClassProperty",2248,8,"SkeletalMeshComponent",0x6e12ac8,0x1c001000000215ULL);
            if(!animation)return false;
            CleaComponentObservation* selected=nullptr;
            if(e33_mesh::named(b,asset,"SK_Alicia_Placeholder","/Game/Characters/Enemies/HumanEnnemies/Alicia/SK_Alicia_Placeholder")){
                if(++out.body_count!=1||component!=body||!e33_mesh::named(b,local_read<uint64_t>(animation),"ABP_Noah_NPC_C","/Game/Characters/Heros/Camps/ABP_Noah_NPC"))return false;
                out.body_material=alicia_materials(b,component,1);selected=&out.body;
            }else if(e33_mesh::named(b,asset,"Maelle_v2_FaceMesh","/Game/MetaHumans/Maelle_v2/Face/Maelle_v2_FaceMesh")){
                if(++out.face_count!=1||!e33_mesh::named(b,local_read<uint64_t>(animation),"Face_NPCSimple_AnimBP_C","/Game/Characters/NPCs/Face_NPCSimple_AnimBP")||
                   !alicia_materials(b,component,15,true))return false;
                selected=&out.face;
            }else if(e33_mesh::named(b,asset,"Hair_Alicia_skl","/Game/Characters/Hair/Mirror_Family/Alicia/Hair_Alicia_skl")){
                if(++out.hair_count!=1||local_read<uint64_t>(animation)||!alicia_materials(b,component,0))return false;
                selected=&out.hair;
            }else{++out.unexpected_skinned_assets;return true;}
            return observe_clea_component(b,component,*selected);
        }
        const auto static_mesh=picto_field(b,component,"StaticMesh","ObjectProperty",1376,8);
        if(!static_mesh)return true;
        if(!component_field(b,component,"StaticMesh","ObjectProperty",1376,8,"StaticMeshComponent",0x6e11d38,0x14c001100000235ULL))return false;
        const auto asset=local_read<uint64_t>(static_mesh);if(!asset)return true;
        if(component==indicator&&e33_mesh::named(b,asset,"Mannequin","/Game/Meshes/Mannequin")){
            uint64_t descriptor=0;
            const auto hidden=component_field(b,component,"bHiddenInGame","BoolProperty",393,1,"SceneComponent",0x6e119b0,0x18001200000015ULL);
            if(!hidden||!picto_field(b,component,"bHiddenInGame","BoolProperty",393,1,&descriptor)||
               !descriptor||local_read<uint32_t>(descriptor+0x70)!=0x08080001U||!(local_read<uint8_t>(hidden)&8))return false;
            return ++indicator_count==1;
        }
        if(e33_mesh::named(b,asset,"SM_mask_alicia","/Game/Characters/Enemies/HumanEnnemies/Alicia/SM_mask_alicia"))
            return ++mask_count==1&&alicia_materials(b,component,0)&&real_renoir_static_pose(b,component,mask);
        if(e33_mesh::named(b,asset,"SM_PaintBrush_01","/Game/Meshes/Manor/SM_PaintBrush_01"))
            return ++brush_count==1&&alicia_materials(b,component,0)&&real_renoir_static_pose(b,component,brush);
        ++unexpected_static;return true;
    };
    if(!body||!root||!call_identity(b,call_capture(b,root))||local_read<uint64_t>(root+32)!=actor.address||
       !inspect(body)||!e33_owned_actor::visit_components(b,actor.address,[&](uint64_t component){return component==body||inspect(component);}))return false;
    const double zero[]={0,0,0},unit[]={1,1,1},body_location[]={0,0,-88},body_rotation[]={0,-90,0};
    const double hair_location[]={18.527771,1.0907,-0.455453},hair_rotation[]={-89.4804,90,-90},hair_scale[]={1.06,1.06,1.06};
    const double mask_location[]={-144,5.2,0.0766196665853212},mask_rotation[]={-90,0,358.0227648040041},mask_scale[]={1.0727272033691406,1,1};
    const double brush_location[]={-9.963756960076001,1.2733101526752546,4.250184242932597};
    const double brush_rotation[]={7.757418234987251,-24.760430416749756,-119.8798173352975};
    return out.body_count==1&&out.face_count==1&&out.hair_count==1&&!out.unexpected_skinned_assets&&out.body_material&&
        mask_count==1&&brush_count==1&&indicator_count==1&&!unexpected_static&&out.body.parent==root&&out.face.parent==body&&
        out.hair.parent==out.face.component.address&&mask.parent==out.face.component.address&&brush.parent==body&&
        exact_name(b,reinterpret_cast<uint64_t>(&out.face.socket),"None")&&
        exact_name(b,reinterpret_cast<uint64_t>(&out.hair.socket),"Head")&&
        exact_name(b,reinterpret_cast<uint64_t>(&mask.socket),"Head")&&
        exact_name(b,reinterpret_cast<uint64_t>(&brush.socket),"Hand_R")&&
        real_renoir_pose(out.body,body_location,body_rotation,unit)&&real_renoir_pose(out.face,zero,zero,unit)&&
        real_renoir_pose(out.hair,hair_location,hair_rotation,hair_scale)&&
        real_renoir_pose(mask,mask_location,mask_rotation,mask_scale)&&real_renoir_pose(brush,brush_location,brush_rotation,unit)&&call_identity(b,actor);
}
}
