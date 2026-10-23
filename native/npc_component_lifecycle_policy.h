#pragma once
#include "mesh_owner.h"
namespace e33_npc_presentation {
// Exact original classes from the complete four-package/74-function inventory.
// Three have no custom EndPlay and directly inherit ActorComponent; the fourth
// has the separately observed original condition-listener unbind mechanism.
// This permits a controlled original-destruction test, not a live cleanup claim.
inline bool reviewed_component_class(uint64_t base,uint64_t cls){
    static constexpr const char* classes[][2]={
        {"BP_NPCAnimationComponent_C","/Game/Characters/NPCs/Animations/BP_NPCAnimationComponent"},
        {"BP_DialogueCameraControllerComponent_C","/Game/Gameplay/Camera/BP_DialogueCameraControllerComponent"},
        {"BP_RoamingAiComponent_C","/Game/Gameplay/WorldAI/BP_RoamingAiComponent"},
        {"BP_ConditionCheckerComponent_C","/Game/Gameplay/ConditionChecker/BP_ConditionCheckerComponent"}};
    if(!call_capture(base,cls).address||
       !e33_mesh::named(base,local_read<uint64_t>(cls+0x40),"ActorComponent","/Script/Engine"))return false;
    for(const auto& item:classes)if(e33_mesh::named(base,cls,item[0],item[1]))return true;
    return false;
}
inline bool original_clea_possession_defaults(uint64_t base,uint64_t cdo){
    uint64_t player_descriptor=0,ai_descriptor=0;
    const auto player=picto_field(base,cdo,"AutoPossessPlayer","ByteProperty",672,1,&player_descriptor);
    const auto ai=picto_field(base,cdo,"AutoPossessAI","EnumProperty",673,1,&ai_descriptor);
    if(!player||!ai||!player_descriptor||!ai_descriptor||
       local_read<uint64_t>(player_descriptor)!=base+0x6e10420||local_read<uint64_t>(ai_descriptor)!=base+0x6deeee8||
       local_read<uint64_t>(player_descriptor+0x38)!=0x18001040000201ULL||
       local_read<uint64_t>(ai_descriptor+0x38)!=0x18001040000201ULL||
       !e33_mesh::named(base,local_read<uint64_t>(player_descriptor+16)&~uint64_t(1),"Pawn","/Script/Engine")||
       !e33_mesh::named(base,local_read<uint64_t>(ai_descriptor+16)&~uint64_t(1),"Pawn","/Script/Engine")||
       !e33_mesh::named(base,local_read<uint64_t>(ai_descriptor+0x78),"EAutoPossessAI","/Script/Engine"))return false;
    // Exact observed original values; never write a possession override or
    // borrow the player's controller. Require no controller on the instance
    // too; unexpected AI/controller lifecycle is outside this first contract.
    return local_read<uint8_t>(player)==0&&local_read<uint8_t>(ai)==1;
}
}
