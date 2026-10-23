#pragma once
#include "npc_original_admission.h"
#include "owned_component_visit.h"
#include "picto_progression.h"
#include <cmath>

namespace e33_npc_presentation {
struct CleaComponentObservation {
    CallIdentity component{};
    uint64_t parent=0,socket=0;
    int32_t leader_index=0,leader_serial=0;
    double location[3]{},rotation[3]{},scale[3]{};
};
struct CleaAssemblyObservation {
    CleaComponentObservation body{},face{},hair{};
    uint32_t body_count=0,face_count=0,hair_count=0,unexpected_skinned_assets=0;
    bool body_material=false;
};
// Fixed read-only native metadata; no WeakObjectProperty codec extension.
inline uint64_t component_field(uint64_t b,uint64_t component,const char* name,const char* type,
        int offset,int width,const char* owner,uint64_t table,uint64_t flags){
    uint64_t descriptor=0;
    const auto at=picto_field(b,component,name,type,offset,width,&descriptor);
    if(!at||!descriptor||local_read<uint64_t>(descriptor)!=b+table||
       local_read<uint64_t>(descriptor+0x38)!=flags||
       !e33_mesh::named(b,local_read<uint64_t>(descriptor+16)&~uint64_t(1),owner,"/Script/Engine"))return 0;
    return at;
}
inline bool observe_scene_component(uint64_t b,uint64_t component,CleaComponentObservation& out){
    out.component=call_capture(b,component);
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
    for(unsigned i=0;i<3;++i)if(!std::isfinite(out.location[i])||!std::isfinite(out.rotation[i])||
       !std::isfinite(out.scale[i])||std::abs(out.location[i])>1.e7||std::abs(out.rotation[i])>1.e7||std::abs(out.scale[i])>1.e7)return false;
    return true;
}
inline bool observe_clea_component(uint64_t b,uint64_t component,CleaComponentObservation& out){
    if(!observe_scene_component(b,component,out))return false;
    const auto leader=component_field(b,component,"LeaderPoseComponent","WeakObjectProperty",1392,8,"SkinnedMeshComponent",0x6e12118,0x1c00104008021cULL);
    if(!leader)return false;
    out.leader_index=local_read<int32_t>(leader);out.leader_serial=local_read<int32_t>(leader+4);return true;
}
inline bool observe_clea_assembly(uint64_t b,CallIdentity actor,CallIdentity cls,CallIdentity cdo,
        CallIdentity available,CleaAssemblyObservation& out){
    out={};
    if(!TargetPodSchemaOps{b}.context()||!original_class_contract(b,cls,cdo,available)||
       !e33_mesh::named(b,cls.address,"BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract_C",
           "/Game/Characters/Enemies/HumanEnnemies/Clea_v1/BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract")||
       !call_identity(b,actor)||local_read<uint64_t>(actor.address+16)!=cls.address||
       (local_read<uint32_t>(actor.address+8)&0x30))return false;
    const auto mesh=picto_field(b,actor.address,"Mesh","ObjectProperty",792,8);
    const auto capsule=picto_field(b,actor.address,"CapsuleComponent","ObjectProperty",808,8);
    if(!mesh||!capsule)return false;
    const auto body=local_read<uint64_t>(mesh),root=local_read<uint64_t>(capsule);
    auto inspect=[&](uint64_t component){
        if(!call_capture(b,component).address||local_read<uint64_t>(component+32)!=actor.address)return false;
        uint64_t descriptor=0;
        const auto skinned=picto_field(b,component,"SkinnedAsset","ObjectProperty",1384,8,&descriptor);
        if(!skinned)return true; // Other original NPC components are retained, not discarded.
        if(!component_field(b,component,"SkinnedAsset","ObjectProperty",1384,8,"SkinnedMeshComponent",0x6e11d38,0x14c001000000214ULL))return false;
        const auto asset=local_read<uint64_t>(skinned);if(!asset)return true;
        const auto animation=component_field(b,component,"AnimClass","ClassProperty",2248,8,"SkeletalMeshComponent",0x6e12ac8,0x1c001000000215ULL);
        if(!animation)return false;
        CleaComponentObservation* selected_component=nullptr;
        if(e33_mesh::named(b,asset,"SK_Clea","/Game/Characters/Enemies/HumanEnnemies/Clea_v1/SK_Clea")){
            if(++out.body_count!=1||component!=body||!e33_mesh::named(b,local_read<uint64_t>(animation),
               "ABP_Noah_NPC_C","/Game/Characters/Heros/Camps/ABP_Noah_NPC"))return false;
            selected_component=&out.body;
            uint64_t material_descriptor=0;
            const auto materials=picto_field(b,component,"OverrideMaterials","ArrayProperty",1304,16,&material_descriptor);
            if(!materials||!material_descriptor||local_read<uint8_t>(material_descriptor+0x70)&1)return false;
            const auto inner=local_read<uint64_t>(material_descriptor+0x78);
            if(!inner||local_read<uint64_t>(inner)!=b+0x6e11d38||local_read<uint64_t>(inner+16)!=material_descriptor||
               local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=8)return false;
            const auto data=local_read<uint64_t>(materials);
            const auto count=local_read<int32_t>(materials+8),capacity=local_read<int32_t>(materials+12);
            if(count!=1||capacity<count||capacity>1024||data<0x10000||(data&7))return false;
            out.body_material=e33_mesh::candidate_named(b,local_read<uint64_t>(data),"MI_Body_Clea_2",
                "/Game/Characters/Enemies/HumanEnnemies/Clea_v1/Textures/MI_Body_Clea_2");
        }else if(e33_mesh::named(b,asset,"clea_FaceMesh","/Game/MetaHumans/clea/Face/clea_FaceMesh")){
            if(++out.face_count!=1||!e33_mesh::named(b,local_read<uint64_t>(animation),"Face_NPCSimple_AnimBP_C",
               "/Game/Characters/NPCs/Face_NPCSimple_AnimBP"))return false;
            selected_component=&out.face;
        }else if(e33_mesh::named(b,asset,"Clea_Hair_SK_UE5","/Game/Characters/Hair/Mirror_Family/Clea/Clea_Hair_SK_UE5")){
            if(++out.hair_count!=1||local_read<uint64_t>(animation))return false;
            selected_component=&out.hair;
        }else{++out.unexpected_skinned_assets;return true;}
        return observe_clea_component(b,component,*selected_component);
    };
    if(!body||!root||!call_capture(b,root).address||local_read<uint64_t>(root+32)!=actor.address||!inspect(body)||
       !e33_owned_actor::visit_components(b,actor.address,[&](uint64_t component){return component==body||inspect(component);}))return false;
    // Exact original SCS relationships: inherited Face -> CharacterMesh0;
    // Clea's own hair node -> Face, with no socket override. No guessed offsets.
    return out.body_count==1&&out.face_count==1&&out.hair_count==1&&!out.unexpected_skinned_assets&&out.body_material&&
        out.body.parent==root&&out.face.parent==body&&out.hair.parent==out.face.component.address&&
        exact_name(b,reinterpret_cast<uint64_t>(&out.face.socket),"None")&&
        exact_name(b,reinterpret_cast<uint64_t>(&out.hair.socket),"None")&&
        out.body.location[0]==0&&out.body.location[1]==0&&out.body.location[2]==-88&&
        out.body.rotation[0]==0&&out.body.rotation[1]==-90&&out.body.rotation[2]==0&&
        out.body.scale[0]==1&&out.body.scale[1]==1&&out.body.scale[2]==1&&call_identity(b,actor);
}
}
