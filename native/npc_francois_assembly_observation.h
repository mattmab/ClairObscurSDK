#pragma once
#include "npc_alicia_assembly_observation.h"
namespace e33_npc_presentation {
inline bool francois_class(uint64_t b,CallIdentity cls){
    return call_identity(b,cls)&&e33_mesh::named(b,cls.address,"BP_NPC_FrancoisTheTurtle_C",
        "/Game/Characters/Enemies/Esquies_Nest/Francois/BP_NPC_FrancoisTheTurtle");
}
inline bool observe_francois_assembly(uint64_t b,CallIdentity actor,CallIdentity cls,CleaAssemblyObservation& out){
    out={};
    if(!TargetPodSchemaOps{b}.context()||!francois_class(b,cls)||!call_identity(b,actor)||
       local_read<uint64_t>(actor.address+16)!=cls.address||(local_read<uint32_t>(actor.address+8)&0x30))return false;
    const auto capsule=picto_field(b,actor.address,"CapsuleComponent","ObjectProperty",808,8);
    const auto mesh=picto_field(b,actor.address,"Mesh","ObjectProperty",792,8);
    if(!capsule||!mesh)return false;
    const auto root=local_read<uint64_t>(capsule),native_mesh=local_read<uint64_t>(mesh);
    if(!call_capture(b,root).address||!call_capture(b,native_mesh).address)return false;
    unsigned sculptures=0,markers=0;
    auto inspect=[&](uint64_t component){
        if(!call_capture(b,component).address||local_read<uint64_t>(component+32)!=actor.address)return false;
        const auto skinned=picto_field(b,component,"SkinnedAsset","ObjectProperty",1384,8);
        if(skinned&&local_read<uint64_t>(skinned)){++out.unexpected_skinned_assets;return false;}
        const auto at=picto_field(b,component,"StaticMesh","ObjectProperty",1376,8);
        if(!at||!local_read<uint64_t>(at))return true;
        if(!component_field(b,component,"StaticMesh","ObjectProperty",1376,8,"StaticMeshComponent",0x6e11d38,0x14c001100000235ULL))return false;
        const auto asset=local_read<uint64_t>(at);
        CleaComponentObservation observed{};
        if(!observe_scene_component(b,component,observed)||
           !exact_name(b,reinterpret_cast<uint64_t>(&observed.socket),"None"))return false;
        if(e33_mesh::named(b,asset,"francois_low","/Game/Characters/Enemies/Esquies_Nest/Francois/francois_low")){
            const double location[]={-105.27593840907485,-1.1614576407215165,-45.16227792329577};
            const double rotation[]={0,-89.36790949418507,0},scale[]={1,1,1};
            if(++out.body_count!=1||observed.parent!=root||!real_renoir_pose(observed,location,rotation,scale)||!alicia_materials(b,component,0))return false;
            out.body=observed;out.body_material=true;return true;
        }
        if(e33_mesh::named(b,asset,"SM_Francois_Rocks","/Game/Meshes/Common/Esquie_Rocks/SM_Francois_Rocks")){
            const double location[]={92.99999956545543,96.00000000182867,-82.70329144723047};
            const double rotation[]={0,269.758727014717,0},scale[]={3,3.0000000587531406,3.0000000587531406};
            return ++sculptures==1&&observed.parent==root&&real_renoir_pose(observed,location,rotation,scale)&&alicia_materials(b,component,1);
        }
        if(!e33_mesh::named(b,asset,"Mannequin","/Game/Meshes/Mannequin"))return false;
        const auto parent=call_capture(b,observed.parent);
        if(!parent.address||local_read<uint64_t>(parent.address+32)!=actor.address||
           !exact_name(b,parent.address+24,"PlayerLocation"))return false;
        const auto parent_at=component_field(b,parent.address,"AttachParent","ObjectProperty",176,8,"SceneComponent",0x6e11d38,0x14c001100080228ULL);
        if(!parent_at||local_read<uint64_t>(parent_at)!=root)return false;
        uint64_t descriptor=0;
        const auto hidden=component_field(b,component,"bHiddenInGame","BoolProperty",393,1,"SceneComponent",0x6e119b0,0x18001200000015ULL);
        return ++markers==1&&hidden&&picto_field(b,component,"bHiddenInGame","BoolProperty",393,1,&descriptor)&&
            local_read<uint32_t>(descriptor+0x70)==0x08080001U&&(local_read<uint8_t>(hidden)&8);
    };
    return e33_owned_actor::visit_components(b,actor.address,inspect)&&out.body_count==1&&sculptures==1&&markers==1&&
        !out.unexpected_skinned_assets&&call_identity(b,actor);
}
}
