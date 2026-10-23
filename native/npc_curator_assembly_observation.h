#pragma once
#include "npc_alicia_assembly_observation.h"
#include "npc_curator_source_contract.h"
namespace e33_npc_presentation {
inline bool observe_curator_assembly(uint64_t b,CallIdentity actor,CallIdentity cls,CallIdentity cdo,
        CallIdentity available,CleaAssemblyObservation& out){
    out={};CuratorDialogueSource source{};
    if(!curator_source_contract(b,cls,cdo,available,source)||!call_identity(b,actor)||
       local_read<uint64_t>(actor.address+16)!=cls.address||(local_read<uint32_t>(actor.address+8)&0x30))return false;
    const auto mesh=picto_field(b,actor.address,"Mesh","ObjectProperty",792,8);
    const auto capsule=picto_field(b,actor.address,"CapsuleComponent","ObjectProperty",808,8);
    const auto indicator_at=picto_field(b,actor.address,"PlayerLocationIndicator","ObjectProperty",1848,8);
    if(!mesh||!capsule||!indicator_at)return false;
    const auto body=local_read<uint64_t>(mesh),root=local_read<uint64_t>(capsule),indicator=local_read<uint64_t>(indicator_at);
    unsigned markers=0,unexpected_static=0;
    auto inspect=[&](uint64_t component){
        if(!call_capture(b,component).address||local_read<uint64_t>(component+32)!=actor.address)return false;
        const auto skinned=picto_field(b,component,"SkinnedAsset","ObjectProperty",1384,8);
        if(skinned&&local_read<uint64_t>(skinned)){
            if(!component_field(b,component,"SkinnedAsset","ObjectProperty",1384,8,"SkinnedMeshComponent",0x6e11d38,0x14c001000000214ULL))return false;
            const auto asset=local_read<uint64_t>(skinned);
            if(component!=body||!e33_mesh::named(b,asset,"SK_Curator","/Game/Characters/Enemies/HumanEnnemies/Curator/SK_Curator")){
                ++out.unexpected_skinned_assets;return true;
            }
            const auto animation=component_field(b,component,"AnimClass","ClassProperty",2248,8,"SkeletalMeshComponent",0x6e12ac8,0x1c001000000215ULL);
            const auto mode=component_field(b,component,"AnimationMode","ByteProperty",2623,1,"SkeletalMeshComponent",0x6e10420,0x28081040000215ULL);
            if(++out.body_count!=1||!animation||!mode||local_read<uint8_t>(mode)!=0||!e33_mesh::named(b,local_read<uint64_t>(animation),
                "ABP_Humanoid_NPC_Curator_Camp_C","/Game/Characters/Enemies/HumanEnnemies/Curator/ABP_Humanoid_NPC_Curator_Camp"))return false;
            out.body_material=alicia_materials(b,component,0);
            return observe_clea_component(b,component,out.body);
        }
        const auto static_at=picto_field(b,component,"StaticMesh","ObjectProperty",1376,8);
        if(!static_at||!local_read<uint64_t>(static_at))return true;
        if(component!=indicator||!component_field(b,component,"StaticMesh","ObjectProperty",1376,8,"StaticMeshComponent",0x6e11d38,0x14c001100000235ULL)||
           !e33_mesh::named(b,local_read<uint64_t>(static_at),"Mannequin","/Game/Meshes/Mannequin")){
            ++unexpected_static;return true;
        }
        uint64_t descriptor=0;
        const auto hidden=component_field(b,component,"bHiddenInGame","BoolProperty",393,1,"SceneComponent",0x6e119b0,0x18001200000015ULL);
        if(!hidden||!picto_field(b,component,"bHiddenInGame","BoolProperty",393,1,&descriptor)||
           local_read<uint32_t>(descriptor+0x70)!=0x08080001U||!(local_read<uint8_t>(hidden)&8))return false;
        return ++markers==1;
    };
    if(!body||!root||!call_capture(b,root).address||local_read<uint64_t>(root+32)!=actor.address||!inspect(body)||
       !e33_owned_actor::visit_components(b,actor.address,[&](uint64_t component){return component==body||inspect(component);}))return false;
    const double location[]={0,0,-88},rotation[]={0,-90,0},scale[]={1.5,1.5,1.5};
    return out.body_count==1&&out.body_material&&!out.unexpected_skinned_assets&&!unexpected_static&&markers==1&&
        out.body.parent==root&&exact_name(b,reinterpret_cast<uint64_t>(&out.body.socket),"None")&&
        real_renoir_pose(out.body,location,rotation,scale)&&call_identity(b,actor);
}
}
